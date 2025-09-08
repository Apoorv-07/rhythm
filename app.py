import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, InternalServerError
import tempfile
import uuid
import time # Import the time module

from generators.poem_generator import PoemGenerator
from generators.music_generator import MusicGenerator
from generators.animation_generator import AnimationGenerator
from models.database import init_db, get_db_connection, close_db_connection, get_db_cursor
from models.content import ContentModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024# 16MB max file size

# CORS configuration
CORS(app, origins=[
    "http://localhost:3000",
    "https://*.netlify.app",
    "https://*.lovable.dev",
    os.environ.get('FRONTEND_URL', '')
])

# Initialize database
init_db()

# Initialize generators
try:
    poem_gen = PoemGenerator()
    music_gen = MusicGenerator()
    animation_gen = AnimationGenerator()
    logger.info("All generators initialized successfully")
except Exception as e:
    logger.error(f"Error initializing generators: {e}")
    poem_gen = music_gen = animation_gen = None

@app.teardown_appcontext
def close_db(error):
    """Close the database connection on app teardown."""
    close_db_connection()

@app.route('/', methods=['GET'])
def home():
    """API documentation and health check"""
    return jsonify({
        'service': 'Multimodal Creative Studio API',
        'version': '1.0.0',
        'status': 'healthy',
        'endpoints': {
            '/api/generate': 'POST - Generate content from prompt',
            '/api/generate-music-file': 'POST - Generate audio file',
            '/api/health': 'GET - Health check',
            '/api/stats': 'GET - Usage statistics'
        },
        'documentation': 'https://github.com/yourusername/creative-studio-api'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            db_status = 'healthy'
        else:
            db_status = 'unavailable'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = 'error'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'generators': {
            'poem': poem_gen is not None,
            'music': music_gen is not None,
            'animation': animation_gen is not None
        }
    })

@app.route('/api/generate', methods=['POST'])
def generate_content():
    """Main content generation endpoint"""
    start_time = time.time()
    user_id = 'anonymous'
    session_id = str(uuid.uuid4())
    prompt = ''

    try:
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")
        
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        user_id = data.get('user_id', 'anonymous')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not prompt:
            raise BadRequest("Prompt is required and cannot be empty")
        
        if len(prompt) > 500:
            raise BadRequest("Prompt too long. Maximum 500 characters allowed")
        
        options = data.get('options', {})
        
        logger.info(f"Generating content for prompt: {prompt[:50]}...")
        
        results = {}
        errors = {}
        
        try:
            if poem_gen:
                poem = poem_gen.generate(prompt, options.get('poem_style', 'festival'))
                results['poem'] = poem
                logger.info("Poem generated successfully")
            else:
                errors['poem'] = "Poem generator not available"
        except Exception as e:
            logger.error(f"Poem generation error: {e}")
            errors['poem'] = str(e)
        
        try:
            if music_gen:
                music_data = music_gen.generate(prompt, options.get('music_style', 'celebration'))
                results['music'] = music_data
                logger.info("Music data generated successfully")
            else:
                errors['music'] = "Music generator not available"
        except Exception as e:
            logger.error(f"Music generation error: {e}")
            errors['music'] = str(e)
        
        try:
            if animation_gen:
                animation_config = animation_gen.generate(prompt, options.get('animation_style', 'festival'))
                results['animation'] = animation_config
                logger.info("Animation config generated successfully")
            else:
                errors['animation'] = "Animation generator not available"
        except Exception as e:
            logger.error(f"Animation generation error: {e}")
            errors['animation'] = str(e)
        
        content_model = ContentModel()
        try:
            content_id = content_model.save_content(
                prompt=prompt,
                poem=results.get('poem'),
                music=results.get('music'),
                animation=results.get('animation'),
                user_id=user_id,
                session_id=session_id
            )
            results['content_id'] = content_id
        except Exception as e:
            logger.error(f"Database save error: {e}")
        
        response = {
            'status': 'success',
            'prompt': prompt,
            'results': results,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session_id
        }
        
        if errors:
            response['errors'] = errors
            response['status'] = 'partial_success'
        
        response_time_ms = int((time.time() - start_time) * 1000)
        content_model.log_usage(
            endpoint='/api/generate',
            user_id=user_id,
            session_id=session_id,
            prompt=prompt,
            success=True,
            response_time_ms=response_time_ms
        )
        return jsonify(response)
        
    except BadRequest as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        content_model = ContentModel()
        content_model.log_usage(
            endpoint='/api/generate',
            user_id=user_id,
            session_id=session_id,
            prompt=prompt,
            success=False,
            error_message=str(e),
            response_time_ms=response_time_ms
        )
        logger.warning(f"Bad request: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 400
        
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        content_model = ContentModel()
        content_model.log_usage(
            endpoint='/api/generate',
            user_id=user_id,
            session_id=session_id,
            prompt=prompt,
            success=False,
            error_message='Internal server error',
            response_time_ms=response_time_ms
        )
        logger.error(f"Unexpected error in generate_content: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Internal server error. Please try again.',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/generate-music-file', methods=['POST'])
def generate_music_file():
    """Generate actual audio file"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            raise BadRequest("Prompt is required")
        
        if not music_gen:
            raise InternalServerError("Music generator not available")
        
        audio_file_path = music_gen.generate_audio_file(prompt)
        
        if not os.path.exists(audio_file_path):
            raise InternalServerError("Failed to generate audio file")
        
        return send_file(
            audio_file_path,
            as_attachment=True,
            download_name=f'fest_music_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav',
            mimetype='audio/wav'
        )
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating music file: {e}")
        return jsonify({'error': 'Failed to generate music file'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get usage statistics"""
    try:
        content_model = ContentModel()
        stats = content_model.get_stats()
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Failed to retrieve statistics'
        }), 500

@app.route('/api/content/<content_id>', methods=['GET'])
def get_content(content_id):
    """Retrieve previously generated content"""
    try:
        content_model = ContentModel()
        content = content_model.get_content(content_id)
        
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        return jsonify({
            'status': 'success',
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving content: {e}")
        return jsonify({'error': 'Failed to retrieve content'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'status': 'error',
        'error': 'File too large. Maximum size is 16MB.'
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'status': 'error',
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'status': 'error',
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Creative Studio API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)