"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
import re  
from flask import Flask, request, jsonify, send_from_directory
from flask_migrate import Migrate
from api.utils import APIException, generate_sitemap
from api.models import db, User, Categories, Match, Review, BestSharers ,SkillNameEnum ,MatchStatus , update_best_sharers
from api.routes import api
from api.admin import setup_admin
from api.commands import setup_commands
from datetime import timedelta
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt

ENV = "development" if os.getenv("FLASK_DEBUG") == "1" else "production"
static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../public/')
app = Flask(__name__)
app.url_map.strict_slashes = False

# Setup JWT 
app.config["JWT_SECRET_KEY"] = os.getenv("JWT-KEY")
jwt = JWTManager(app)
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)

# Configuración de CORS
cors = CORS(app, resources={r"/*": {"origins": "https://ideal-garbanzo-qjrrvx4jq9pfxr4p-3000.app.github.dev"}})

bcrypt = Bcrypt(app)

# database configuration
db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db, compare_type=True)
db.init_app(app)

# add the admin
setup_admin(app)
setup_commands(app)

# Add all endpoints from the API with a "api" prefix
app.register_blueprint(api, url_prefix='/api')

@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code
@app.route('/')
def sitemap():
    if ENV == "development":
        return generate_sitemap(app)
    return send_from_directory(static_file_dir, 'index.html')
@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = 'index.html'
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0  # avoid cache memory
    return response


#Our Endpoints
#SINGUP LOGIN AND PRIVATE PROFILE:

@app.route("/signup", methods=["POST"])
def create_user():
    body = request.get_json(silent=True)

    if body is None:
        return jsonify({'msg': 'Body is required'}), 400
    if 'email' not in body:
        return jsonify({'msg': 'Field "email" is required'}), 400
    if 'password' not in body:
        return jsonify({'msg': 'Field "password" is required'}), 400

    existing_user = User.query.filter_by(email=body['email']).first()
    if existing_user:
        return jsonify({'msg': 'Email already exists in the database'}), 400
    is_active = body.get('is_active', True)

    if not re.match(r"[^@]+@[^@]+\.[^@]+", body['email']):
        return jsonify({'msg': 'Invalid email format'}), 400

    if len(body['password']) < 8:
        return jsonify({'msg': 'Password must be at least 8 characters long'}), 400

    try:
        pw_hash = bcrypt.generate_password_hash(body['password']).decode('utf-8')
        new_user = User(email=body['email'], password=pw_hash, is_active=is_active)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'msg': 'New User Created', 'user_id': new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': str(e)}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        body = request.get_json(silent=True)
        
        if body is None:
            return jsonify({'msg': 'Body is required'}), 400
        if 'email' not in body:
            return jsonify({'msg': 'Field "email" is required'}), 400
        if 'password' not in body:
            return jsonify({'msg': 'Field "password" is required'}), 400

        user = User.query.filter_by(email=body['email']).first()

        if not user:
            return jsonify({'msg': "User not found"}), 404
        if not user.is_active:
            return jsonify({'msg': 'User account is inactive'}), 403
        if not bcrypt.check_password_hash(user.password, body['password']):
            return jsonify({'msg': "Bad email or password"}), 401

        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    
    except Exception as e:
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/update_user', methods=['PUT'])
@jwt_required()
def update_user():
    body = request.get_json(silent=True)
    
    if body is None:
        return jsonify({'msg': 'Body is required'}), 400

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Track how many fields are updated
    updated_fields = 0

    name = body.get('name')
    if name:
        if len(name) < 2 or len(name) > 30:
            return jsonify({"error": "Name must be between 2 and 30 characters"}), 400
        user.name = name
        updated_fields += 1

    email = body.get('email')
    if email:
        # Check if the email format is valid using a regular expression
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Ensure the email is not already used by another user
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != current_user_id:
            return jsonify({"error": "Email already exists"}), 400

        user.email = email
        updated_fields += 1

    last_name = body.get('last_name')
    if last_name:
        if len(last_name) < 2 or len(last_name) > 30:
            return jsonify({"error": "Last name must be between 2 and 30 characters"}), 400
        user.last_name = last_name
        updated_fields += 1

    phone = body.get('phone')
    if phone:
        # Basic validation: only numbers, spaces, and dashes allowed
        if not re.match(r'^\+?[0-9\s\-]+$', phone):
            return jsonify({"error": "Invalid phone number format"}), 400
        user.phone = phone
        updated_fields += 1

    location = body.get('location')
    if location:
        if len(location) < 2 or len(location) > 50:
            return jsonify({"error": "Location must be between 2 and 50 characters"}), 400
        user.location = location
        updated_fields += 1

    # Check if any fields were updated
    if updated_fields == 0:
        return jsonify({"message": "No fields were updated"}), 400

    try:
        db.session.commit()
        return jsonify({"message": "User updated successfully", "user": user.serialize()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An error occurred while updating the user", "details": str(e)}), 500

@app.route("/profile", methods=["GET"])
@jwt_required()
def get_private_info():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'msg': 'User not found'}), 404

    return jsonify({
        'msg': 'Info correct, you logged in!',
        'user_data': user.serialize()  
    })


#SEARCH & SKILLS:

@app.route('/users', methods=['GET'])
def list_users():
    users = User.query.all()
    return jsonify({'users': [user.serialize() for user in users]}), 200

@app.route('/search/users', methods=['GET'])
def search_users():
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({'msg': 'Query parameter is required'}), 400
    
    # Search user with that info in all fields
    users = User.query.filter(
        (User.name.ilike(f'%{query}%')) |
        (User.email.ilike(f'%{query}%')) |
        (User.last_name.ilike(f'%{query}%')) |
        (User.location.ilike(f'%{query}%')) |
        (User.language.ilike(f'%{query}%')) |
        (User.profile_pic.ilike(f'%{query}%')) |
        (User.description.ilike(f'%{query}%')) |
        (User.phone.ilike(f'%{query}%'))
    ).all()
    
    if not users:
        return jsonify({'msg': 'No users found'}), 404
    
    return jsonify({'users': [user.serialize() for user in users]}), 200

@app.route('/search/users/skill', methods=['GET'])
def search_users_by_skill():
    skill = request.args.get('skill', '')
    
    if not skill:
        return jsonify({'msg': 'Skill parameter is required'}), 400
    
    try:
        # Usa CAST para convertir el tipo enum a texto
        users = db.session.query(User).join(Categories).filter(
            Categories.skill_name.cast(db.String).ilike(f'%{skill}%')
        ).all()
        
        if not users:
            return jsonify({'msg': 'No users found with the specified skill'}), 404
        
        return jsonify({'users': [user.serialize() for user in users]}), 200
    
    except Exception as e:
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/add/skill', methods=['POST'])
@jwt_required()
def add_skill():
    try:
        user_id = get_jwt_identity()
        skill = request.json.get('skill', '')
        description = request.json.get('description', '')

        if not skill:
            return jsonify({'msg': 'Skill is required'}), 400

        # Verify if the skill is a valid category
        valid_skills = {e.value for e in SkillNameEnum}
        if skill not in valid_skills:
            return jsonify({'msg': 'Invalid skill category'}), 400

        # Max 5 skills for example
        existing_skills_count = Categories.query.filter_by(user_id=user_id).count()
        if existing_skills_count >= 5:
            return jsonify({'msg': 'Cannot add more than 5 skills'}), 400

        existing_skill = Categories.query.filter_by(user_id=user_id, skill_name=skill).first()
        
        if existing_skill:
            return jsonify({'msg': 'Skill already added'}), 400
        
        new_skill = Categories(user_id=user_id, skill_name=skill, description=description)
        db.session.add(new_skill)
        db.session.commit()

        return jsonify({
            'msg': 'Skill added successfully',
            'user_id': user_id,
            'skill': skill,
            'description': description
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500
    
@app.route('/update/skill/<string:skill_name>', methods=['PUT'])
@jwt_required()
def update_skill(skill_name):
    try:
        user_id = get_jwt_identity()
        new_description = request.json.get('description', '')

        if not new_description:
            return jsonify({'msg': 'Description is required'}), 400

        # Verify if the skill is a valid category
        valid_skills = {e.value for e in SkillNameEnum}
        if skill_name not in valid_skills:
            return jsonify({'msg': 'Invalid skill category'}), 400

        skill = Categories.query.filter_by(user_id=user_id, skill_name=skill_name).first()

        if not skill:
            return jsonify({'msg': 'Skill not found'}), 404
        
        skill.description = new_description
        db.session.commit()

        return jsonify({
            'msg': 'Skill updated successfully',
            'user_id': user_id,
            'skill': skill_name,
            'description': new_description
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/delete/skill/<string:skill_name>', methods=['DELETE'])
@jwt_required()
def delete_skill(skill_name):
    try:
        user_id = get_jwt_identity()

        # Verify if the skill is a valid category
        valid_skills = {e.value for e in SkillNameEnum}
        if skill_name not in valid_skills:
            return jsonify({'msg': 'Invalid skill category'}), 400

        skill = Categories.query.filter_by(user_id=user_id, skill_name=skill_name).first()

        if not skill:
            return jsonify({'msg': 'Skill not found'}), 404

        db.session.delete(skill)
        db.session.commit()

        return jsonify({
            'msg': 'Skill deleted successfully',
            'user_id': user_id,
            'skill': skill_name
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500


#REVIEWS AND BESTSHARERS:

@app.route('/add/review', methods=['POST'])
@jwt_required()
def add_review():
    try:
        reviewer_id = get_jwt_identity()
        reviewee_id = request.json.get('reviewee_id', '')
        score = request.json.get('score', '')
        comment = request.json.get('comment', '')

        if not reviewee_id or not score:
            return jsonify({'msg': 'Reviewee ID and score are required'}), 400
        if reviewer_id == reviewee_id:
            return jsonify({'msg': 'You can not review yourself!'}), 400

        reviewer = User.query.get(reviewer_id)
        reviewee = User.query.get(reviewee_id)

        if not reviewer or not reviewee:
            return jsonify({'msg': 'Reviewer or reviewee does not exist'}), 404

        existing_review = Review.query.filter_by(reviewer_id=reviewer_id, reviewee_id=reviewee_id).first()
        if existing_review:
            return jsonify({'msg': 'Review already exists between these users'}), 400

        new_review = Review(reviewer_id=reviewer_id, reviewee_id=reviewee_id, score=score, comment=comment)
        db.session.add(new_review)
        db.session.commit()

        update_best_sharers()

        return jsonify({
            'review_id': new_review.id,  'msg': 'Review added successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/update/review/<int:review_id>', methods=['PUT'])
@jwt_required()
def update_review(review_id):
    try:
        reviewer_id = get_jwt_identity()
        review = Review.query.get(review_id)

        if not review:
            return jsonify({'msg': 'Review not found'}), 404

        if review.reviewer_id != reviewer_id:
            return jsonify({'msg': 'You can only update your own reviews'}), 403

        score = request.json.get('score', '')
        comment = request.json.get('comment', '')

        if score is not None:
            review.score = score
        if comment:
            review.comment = comment

        db.session.commit()
        update_best_sharers()

        return jsonify({
            'msg': 'Review updated successfully',
            'review_id': review.id,  
            'review': {
                'reviewer_id': review.reviewer_id,
                'reviewee_id': review.reviewee_id,
                'score': review.score,
                'comment': review.comment
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    try:
        user_id = get_jwt_identity()
        review = Review.query.filter_by(id=review_id, reviewer_id=user_id).first()

        if not review:
            return jsonify({'msg': 'Review not found or not authorized'}), 404

        db.session.delete(review)
        db.session.commit()

        update_best_sharers()

        return jsonify({
            'msg': 'Review deleted successfully',
            'review_id': review.id 
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/bestsharers', methods=['GET'])
def best_sharers():
    try:
        users = User.query.all()

        users_with_scores = [
            (user, user.calculate_average_score() if user.reviews_received.count() > 0 else 0)
            for user in users
        ]

        sorted_users = sorted(users_with_scores, key=lambda x: x[1], reverse=True)

        top_users = sorted_users[:6]

        if not top_users:
            return jsonify({'msg': 'No users found'}), 404

        return jsonify({
            'best_sharers': [
                {
                    'user': user.serialize(),
                    'average_score': average_score
                } for user, average_score in top_users
            ]
        }), 200
    except Exception as e:
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/user/<int:user_id>/reviews', methods=['GET']) #To know all reviews of an user, just if we need it
def get_user_reviews(user_id):
    reviews = Review.query.filter_by(reviewee_id=user_id).all()
    if not reviews:
        return jsonify({'msg': 'No reviews found for this user'}), 404

    return jsonify({
        'reviews': [
            {
                'id': review.id,
                'reviewer_id': review.reviewer_id,
                'score': review.score,
                'comment': review.comment
            } for review in reviews
        ]
    }), 200


#MATCHS (Adding people):

@app.route('/match/<int:match_id>', methods=['GET'])
@jwt_required()
def get_match(match_id):
    try:
        user_id = get_jwt_identity()
        match = Match.query.filter_by(match_id=match_id).first()

        if not match:
            return jsonify({'msg': 'Match not found'}), 404

        if match.match_to_id != user_id and match.match_from_id != user_id:
            return jsonify({'msg': 'You are not authorized to view this match'}), 403

        return jsonify({
            'match_id': match.match_id,
            'match_from_id': match.match_from_id,
            'match_to_id': match.match_to_id,
            'match_status': match.match_status
        }), 200

    except Exception as e:
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/match', methods=['POST'])
@jwt_required()
def create_match():
    try:
        match_from_id = get_jwt_identity()
        match_to_id = request.json.get('match_to_id')

        if not match_to_id:
            return jsonify({'msg': 'Match to ID is required'}), 400

        if match_from_id == match_to_id:
            return jsonify({'msg': 'You cannot match with yourself!'}), 400

        match_to = User.query.get(match_to_id)
        if not match_to:
            return jsonify({'msg': 'User to match with does not exist'}), 404

        existing_match = Match.query.filter_by(match_from_id=match_from_id, match_to_id=match_to_id).first()
        if existing_match:
            return jsonify({'msg': 'Match request already exists'}), 400

        new_match = Match(
            match_from_id=match_from_id,
            match_to_id=match_to_id,
            match_status=MatchStatus.PENDING.value  
        )
        db.session.add(new_match)
        db.session.commit()

        return jsonify({'msg': 'Match request sent successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/match/<int:match_id>', methods=['PUT'])
@jwt_required()
def update_match(match_id):
    try:
        user_id = get_jwt_identity()
        match = Match.query.get(match_id)

        if not match:
            return jsonify({'msg': 'Match not found'}), 404

        if match.match_to_id != user_id and match.match_from_id != user_id:
            return jsonify({'msg': 'You can only update your own matches'}), 403

        match_status = request.json.get('match_status')
        if match_status not in [status.value for status in MatchStatus]:
            return jsonify({'msg': 'Invalid match status'}), 400

        match.match_status = match_status
        db.session.commit()

        return jsonify({'msg': 'Match status updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500

@app.route('/match/<int:match_id>', methods=['DELETE'])
@jwt_required()
def delete_match(match_id):
    try:
        user_id = get_jwt_identity()
        match = Match.query.filter_by(match_id=match_id, match_from_id=user_id).first()

        if not match:
            return jsonify({'msg': 'Match not found or not authorized'}), 404

        db.session.delete(match)
        db.session.commit()

        return jsonify({'msg': 'Match request canceled successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'An error occurred', 'error': str(e)}), 500


#FLASK-MAIL






@app.route('/profile/<int:user_id>', methods=['GET'])
def view_user_profile(user_id):
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'msg': 'User not found'}), 404
    
    return jsonify({'user_data': user.serialize()}), 200

@app.route('/our/profiles', methods=['GET'])
def our_profiles():
    # Hardcoded example, you could fetch from a database or configuration
    profiles = [
        {'name': 'John Doe', 'email': 'john@example.com', 'description': 'Profile 1'},
        {'name': 'Jane Smith', 'email': 'jane@example.com', 'description': 'Profile 2'},
        {'name': 'Alice Johnson', 'email': 'alice@example.com', 'description': 'Profile 3'}
    ]
    
    return jsonify({'profiles': profiles}), 200


# this only runs if `$ python src/main.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=PORT, debug=True)
