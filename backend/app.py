from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Your MySQL username
    'password': '',  # Your MySQL password
    'database': 'dig_id'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Officer Authentication Routes
@app.route('/api/officer/signup', methods=['POST'])
def officer_signup():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['idNumber', 'email', 'phoneNumber', 'fullName', 'station', 'constituency', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if officer already exists
        cursor.execute("SELECT id FROM officers WHERE id_number = %s OR email = %s", 
                      (data['idNumber'], data['email']))
        if cursor.fetchone():
            return jsonify({'error': 'Officer with this ID number or email already exists'}), 400
        
        # Hash password
        hashed_password = generate_password_hash(data['password'])
        
        # Insert new officer (pending approval)
        cursor.execute("""
            INSERT INTO officers (id_number, email, phone_number, full_name, station, constituency, password_hash, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
        """, (data['idNumber'], data['email'], data['phoneNumber'], 
              data['fullName'], data['station'], data['constituency'], hashed_password, datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Application submitted successfully. Awaiting admin approval.'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/officer/login', methods=['POST'])
def officer_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get officer details including constituency
        cursor.execute("""
            SELECT id, email, full_name, station, constituency, password_hash, status 
            FROM officers WHERE email = %s
        """, (email,))
        officer = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not officer:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if officer['status'] == 'suspended':
            return jsonify({'error': 'Account suspended. Contact admin.'}), 403
        if officer['status'] != 'approved':
            return jsonify({'error': 'Account not approved by admin'}), 403
        
        if not check_password_hash(officer['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token = jwt.encode({
            'officer_id': officer['id'],
            'email': officer['email'],
            'role': 'officer',
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'officer': {
                'id': officer['id'],
                'email': officer['email'],
                'fullName': officer['full_name'],
                'station': officer['station'],
                'constituency': officer['constituency']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin Authentication
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get admin details
        cursor.execute("""
            SELECT id, username, full_name, password_hash 
            FROM admins WHERE username = %s
        """, (username,))
        admin = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not admin:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not check_password_hash(admin['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token = jwt.encode({
            'admin_id': admin['id'],
            'username': admin['username'],
            'role': 'admin',
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'admin': {
                'id': admin['id'],
                'username': admin['username'],
                'fullName': admin['full_name']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Constituency Management Routes
@app.route('/api/constituencies', methods=['GET'])
def get_constituencies():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, name, created_at FROM constituencies ORDER BY name")
        constituencies = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'constituencies': constituencies}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/constituencies', methods=['POST'])
def add_constituency():
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Constituency name is required'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if constituency already exists
        cursor.execute("SELECT id FROM constituencies WHERE name = %s", (name,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Constituency already exists'}), 400
        
        cursor.execute("INSERT INTO constituencies (name, created_at) VALUES (%s, %s)", 
                      (name, datetime.now()))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Constituency added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/constituencies/<int:constituency_id>', methods=['DELETE'])
def delete_constituency(constituency_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM constituencies WHERE id = %s", (constituency_id,))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Constituency not found'}), 404
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Constituency deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin Routes
@app.route('/api/admin/officers/pending', methods=['GET'])
def get_pending_officers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, id_number, email, phone_number, full_name, station, created_at
            FROM officers WHERE status = 'pending'
            ORDER BY created_at DESC
        """)
        officers = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'officers': officers}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/officers/<int:officer_id>/approve', methods=['PUT'])
def approve_officer(officer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE officers SET status = 'approved' WHERE id = %s", (officer_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Officer approved successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/officers/<int:officer_id>/reject', methods=['PUT'])
def reject_officer(officer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE officers SET status = 'rejected' WHERE id = %s", (officer_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Officer rejected'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Application Routes
@app.route('/api/applications', methods=['POST'])
def submit_application():
    try:
        print("Received request:", request.method, request.content_type)
        
        # Check content type
        if request.content_type and 'application/json' in request.content_type:
            # Handle JSON data
            data = request.get_json()
            files = {}
            print("Processing JSON data:", list(data.keys()) if data else "No data")
        else:
            # Handle form data with files
            data = request.form.to_dict()
            files = request.files
            print("Processing form data:", list(data.keys()) if data else "No data")
        
        # Validate required fields
        required_fields = ['fullNames', 'dateOfBirth', 'gender', 'fatherName', 'motherName', 
                          'districtOfBirth', 'tribe', 'homeDistrict', 'division', 
                          'constituency', 'location', 'subLocation', 'villageEstate', 'occupation']
        
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print("Missing required fields:", missing_fields)
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Open connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Determine submitting officer
        officer_id = None

        # Try JWT from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                officer_id = payload.get('officer_id')
            except Exception as e:
                print('JWT decode failed:', e)

        # Fallback to explicit officerId in payload
        if not officer_id:
            officer_id = data.get('officerId')

        # Validate officer
        if not officer_id:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Officer ID missing'}), 400

        cursor.execute("SELECT id FROM officers WHERE id = %s AND status = 'approved'", (officer_id,))
        officer_result = cursor.fetchone()
        if not officer_result:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid or unapproved officer'}), 400

        # Generate application number (sequential per total count)
        cursor.execute("SELECT COUNT(*) FROM applications")
        count = cursor.fetchone()[0]
        application_number = f"APP{datetime.now().year}{count + 1:06d}"
        
        print(f"Generated application number: {application_number}")
        
        # Insert application
        cursor.execute("""
            INSERT INTO applications (
                application_number, officer_id, application_type,
                full_names, date_of_birth, gender, father_name, mother_name,
                marital_status, husband_name, husband_id_no,
                district_of_birth, tribe, clan, family, home_district,
                division, constituency, location, sub_location, village_estate,
                home_address, occupation, supporting_documents, status, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            application_number, officer_id, 'new',
            data['fullNames'], data['dateOfBirth'], data['gender'],
            data['fatherName'], data['motherName'], data.get('maritalStatus'),
            data.get('husbandName'), data.get('husbandIdNo'),
            data['districtOfBirth'], data['tribe'], data.get('clan'),
            data.get('family'), data['homeDistrict'], data['division'],
            data['constituency'], data['location'], data['subLocation'],
            data['villageEstate'], data.get('homeAddress'), data['occupation'],
            json.dumps(data.get('supportingDocuments', {})), 'submitted', datetime.now()
        ))
        
        application_id = cursor.lastrowid
        
        # Handle file uploads (only if files were sent)
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        for file_key, file in files.items():
            if file and file.filename:
                # Create safe filename
                filename = f"{application_number}_{file_key}_{file.filename}"
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Map file types
                doc_type_mapping = {
                    'passportPhoto': 'passport_photo',
                    'birthCertificate': 'birth_certificate', 
                    'parentsId': 'parent_id_front'
                }
                
                doc_type = doc_type_mapping.get(file_key, file_key)
                
                # Insert document record
                cursor.execute("""
                    INSERT INTO documents (application_id, document_type, file_path)
                    VALUES (%s, %s, %s)
                """, (application_id, doc_type, file_path))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'applicationNumber': application_number
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/applications/track/<application_number>', methods=['GET'])
def track_application(application_number):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT application_number, full_names, status, created_at, updated_at
            FROM applications WHERE application_number = %s
        """, (application_number,))
        
        application = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not application:
            return jsonify({'error': 'Application not found'}), 404
            
        return jsonify({'application': application}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/officers/approved', methods=['GET'])
def get_approved_officers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, id_number, email, phone_number, full_name, station, status, created_at
            FROM officers WHERE status IN ('approved', 'suspended')
            ORDER BY created_at DESC
        """)
        officers = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'officers': officers}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications', methods=['GET'])
def get_all_applications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get only pending applications (submitted status)
        cursor.execute("""
            SELECT a.id, a.application_number, a.full_names, a.status, 
                   a.application_type, a.created_at, a.updated_at,
                   o.full_name as officer_name
            FROM applications a 
            LEFT JOIN officers o ON a.officer_id = o.id
            WHERE a.status = 'submitted'
            ORDER BY a.created_at DESC
        """)
        
        applications = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'applications': applications}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/history', methods=['GET'])
def get_application_history():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all applications regardless of status
        cursor.execute("""
            SELECT a.id, a.application_number, a.full_names, a.status, 
                   a.application_type, a.created_at, a.updated_at,
                   a.generated_id_number, o.full_name as officer_name
            FROM applications a 
            LEFT JOIN officers o ON a.officer_id = o.id
            ORDER BY a.created_at DESC
        """)
        
        applications = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'applications': applications}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/<int:application_id>', methods=['GET'])
def get_application_details(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get application details
        cursor.execute("""
            SELECT a.*, o.full_name as officer_name
            FROM applications a 
            LEFT JOIN officers o ON a.officer_id = o.id
            WHERE a.id = %s
        """, (application_id,))
        
        application = cursor.fetchone()
        
        if not application:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        # Get supporting documents
        cursor.execute("""
            SELECT document_type, file_path
            FROM documents WHERE application_id = %s
        """, (application_id,))
        
        documents = cursor.fetchall()
        application['documents'] = documents
        
        cursor.close()
        conn.close()
        
        return jsonify({'application': application}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/<int:application_id>/approve', methods=['PUT'])
def approve_application(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        print(f"[approve_application] Start - application_id={application_id}")

        # Get application details to check if it's a renewal
        cursor.execute("""
            SELECT application_type, existing_id_number 
            FROM applications 
            WHERE id = %s
        """, (application_id,))
        app_details = cursor.fetchone()
        print(f"[approve_application] app_details={app_details}")

        if not app_details:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found'}), 404

        # Handle approvals differently for new applications vs renewals
        if app_details['application_type'] == 'renewal' and app_details['existing_id_number']:
            # For renewals, just update status - don't change the generated_id_number
            id_number = app_details['existing_id_number']
            cursor.execute("""
                UPDATE applications 
                SET status = 'approved', updated_at = %s
                WHERE id = %s
            """, (datetime.now(), application_id))
        else:
            # Generate new ID number for new applications using proper sequence
            year = datetime.now().year
            prefix = f"ID{year}"

            # Note: avoid passing a value with '%' via params; use CONCAT to append wildcard in SQL.
            cursor.execute("""
                SELECT COALESCE(MAX(CAST(SUBSTRING(generated_id_number, 7) AS UNSIGNED)), 0) AS max_id
                FROM applications
                WHERE generated_id_number LIKE CONCAT(%s, '%%')
            """, (prefix,))
            result = cursor.fetchone()
            max_id = result['max_id'] if result and result['max_id'] is not None else 0

            print(f"[approve_application] year={year}, prefix={prefix}, max_id={max_id}")

            # Build next ID number
            id_number = f"{prefix}{int(max_id) + 1:08d}"

            # Update application status and assign new ID number
            cursor.execute("""
                UPDATE applications 
                SET status = 'approved', generated_id_number = %s, updated_at = %s
                WHERE id = %s
            """, (id_number, datetime.now(), application_id))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found'}), 404

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[approve_application] Success - application_id={application_id}, id_number={id_number}")

        return jsonify({
            'message': 'Application approved successfully',
            'id_number': id_number
        }), 200

    except Exception as e:
        # Log the error for debugging
        print(f"[approve_application] Error - application_id={application_id}, error={e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/<int:application_id>/reject', methods=['PUT'])
def reject_application(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update application status
        cursor.execute("""
            UPDATE applications 
            SET status = 'rejected', updated_at = %s
            WHERE id = %s
        """, (datetime.now(), application_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Application rejected successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/dispatch', methods=['GET'])
def get_dispatch_applications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT a.id, a.application_number, a.full_names, a.application_type, 
                   a.generated_id_number, a.created_at, a.updated_at, o.full_name as officer_name
            FROM applications a
            LEFT JOIN officers o ON a.officer_id = o.id
            WHERE a.status = 'ready_for_dispatch'
            ORDER BY a.updated_at DESC
        """
        
        cursor.execute(query)
        applications = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'applications': applications}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/preview', methods=['GET'])
def get_preview_applications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT a.id, a.application_number, a.full_names, a.application_type, 
                   a.generated_id_number, a.created_at, a.updated_at, o.full_name as officer_name
            FROM applications a
            LEFT JOIN officers o ON a.officer_id = o.id
            WHERE a.status = 'approved'
            ORDER BY a.updated_at DESC
        """
        
        cursor.execute(query)
        applications = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'applications': applications}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/<int:application_id>/print', methods=['PUT'])
def print_application(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update application status to 'ready_for_dispatch' (printed, ready for dispatch)
        cursor.execute("""
            UPDATE applications 
            SET status = 'ready_for_dispatch', updated_at = %s
            WHERE id = %s AND status = 'approved'
        """, (datetime.now(), application_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found or not in approved status'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Application marked as printed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/applications/<int:application_id>/dispatch', methods=['PUT'])
def dispatch_application(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update application status to dispatched
        cursor.execute("""
            UPDATE applications 
            SET status = 'dispatched', updated_at = %s
            WHERE id = %s AND status = 'ready_for_dispatch'
        """, (datetime.now(), application_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found or not approved'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Application dispatched successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Officer Application Management Routes
@app.route('/api/officer/applications', methods=['GET'])
def get_officer_applications():
    try:
        # In a real app, get officer_id from JWT token
        officer_id = request.args.get('officer_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First get the officer's constituency and station
        cursor.execute("SELECT station, constituency FROM officers WHERE id = %s", (officer_id,))
        officer_result = cursor.fetchone()
        
        if not officer_result:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Officer not found'}), 404
        
        officer_station = (officer_result[0] or '').strip()
        officer_constituency = (officer_result[1] or '').strip()
        
        # Prefer constituency, but fall back to station if constituency is missing
        location_key = officer_constituency if officer_constituency else officer_station
        
        if not location_key:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Officer has no constituency or station set'}), 400
        
        # Get all applications from the officer's constituency or ones processed by this officer
        cursor.execute("""
            SELECT id, application_number, full_names, status, created_at, 
                   updated_at, generated_id_number
            FROM applications 
            WHERE (TRIM(constituency) = %s OR officer_id = %s)
            ORDER BY created_at DESC
        """, (location_key, officer_id,))
        
        applications = []
        for row in cursor.fetchall():
            app = {
                'id': row[0],
                'application_number': row[1],
                'full_names': row[2],
                'status': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'updated_at': row[5].isoformat() if row[5] else None,
                'generated_id_number': row[6]
            }
            applications.append(app)
        
        cursor.close()
        conn.close()
        
        return jsonify(applications), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/officer/applications/<int:application_id>/card-arrived', methods=['PUT'])
def mark_card_arrived(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE applications 
            SET status = 'ready_for_collection', updated_at = %s 
            WHERE id = %s AND status = 'dispatched'
        """, (datetime.now(), application_id))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Application not found or not in dispatched status'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Card arrival confirmed'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/officer/applications/<int:application_id>/card-collected', methods=['PUT'])
def mark_card_collected(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE applications 
            SET status = 'collected', updated_at = %s 
            WHERE id = %s AND (status = 'ready_for_collection' OR (status IN ('', 'dispatched') AND generated_id_number IS NOT NULL))
        """, (datetime.now(), application_id))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Application not found or card not arrived yet'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Card collection confirmed'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Lost ID Replacement Routes
@app.route('/api/applications/search-by-id/<id_number>', methods=['GET'])
def search_application_by_id(id_number):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, application_number, full_names, date_of_birth, 
                   generated_id_number, status, father_name, mother_name, home_district
            FROM applications 
            WHERE generated_id_number = %s AND status IN ('approved', 'dispatched', 'ready_for_collection', 'collected')
        """, (id_number,))
        
        application = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not application:
            return jsonify({'error': 'ID not found or not issued yet'}), 404
            
        return jsonify({'application': application}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/applications/lost-id', methods=['POST'])
def submit_lost_id_application():
    try:
        print("Received lost ID application request")
        
        # Handle form data with files
        data = request.form.to_dict()
        files = request.files
        print("Processing lost ID form data:", list(data.keys()) if data else "No data")
        
        # Validate required fields
        required_fields = ['existing_id_number', 'ob_number', 'full_names']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print("Missing required fields:", missing_fields)
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Get officer ID from JWT token if provided; otherwise leave as NULL
        officer_id = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                officer_id = payload.get('officer_id')
            except Exception as e:
                print('JWT decode failed in lost-id:', e)
        
        # Open DB connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validate officer_id (must exist and be approved) or set to NULL
        if officer_id:
            cursor.execute("SELECT id FROM officers WHERE id = %s AND status = 'approved'", (officer_id,))
            if cursor.fetchone() is None:
                officer_id = None
        
        # Get current count for application number
        cursor.execute("SELECT COUNT(*) FROM applications WHERE application_type = 'renewal'")
        count = cursor.fetchone()[0]
        application_number = f"REP{datetime.now().year}{count + 1:06d}"
        
        print(f"Generated application number: {application_number}")
        
        # Insert lost ID application
        cursor.execute("""
            INSERT INTO applications (
                application_number, officer_id, application_type,
                full_names, date_of_birth, father_name, mother_name, home_district,
                existing_id_number, renewal_reason, ob_number, constituency,
                status, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            application_number, officer_id, 'renewal',
            data['full_names'], data.get('date_of_birth'), 
            data.get('father_name'), data.get('mother_name'), data.get('home_district'),
            data['existing_id_number'], 'lost', data['ob_number'], data.get('constituency'),
            'submitted', datetime.now()
        ))
        
        application_id = cursor.lastrowid
        
        # Handle file uploads
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        # Define expected files for lost ID applications
        file_mappings = {
            'ob_photo': 'ob_photo',
            'passport_photo': 'passport_photo', 
            'birth_certificate': 'birth_certificate'
        }
        
        for file_key, doc_type in file_mappings.items():
            if file_key in files and files[file_key].filename:
                file = files[file_key]
                # Create safe filename
                filename = f"{application_number}_{file_key}_{file.filename}"
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                # Insert document record
                cursor.execute("""
                    INSERT INTO documents (application_id, document_type, file_path)
                    VALUES (%s, %s, %s)
                """, (application_id, doc_type, file_path))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Lost ID application submitted successfully',
            'applicationNumber': application_number,
            'applicationId': application_id
        }), 201
        
    except Exception as e:
        print(f"Error in lost ID application: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments', methods=['POST'])
def submit_payment():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['application_id', 'amount', 'payment_method']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert payment record
        cursor.execute("""
            INSERT INTO payments (application_id, amount, payment_method, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['application_id'], data['amount'], data['payment_method'], 
            data.get('status', 'pending'), datetime.now()
        ))
        
        payment_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Payment submitted successfully',
            'paymentId': payment_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/applications/<int:application_id>/submit-for-approval', methods=['PUT'])
def submit_for_approval(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update application status to indicate it's submitted for approval
        cursor.execute("""
            UPDATE applications 
            SET status = 'submitted', updated_at = %s
            WHERE id = %s
        """, (datetime.now(), application_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Application submitted for approval'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/officers/<int:officer_id>/suspend', methods=['PUT'])
def suspend_officer(officer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE officers SET status = 'suspended' WHERE id = %s", (officer_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Officer suspended successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/officers/<int:officer_id>/unsuspend', methods=['PUT'])
def unsuspend_officer(officer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE officers SET status = 'approved' WHERE id = %s", (officer_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Officer unsuspended successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/officers/<int:officer_id>', methods=['DELETE'])
def delete_officer(officer_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM officers WHERE id = %s", (officer_id,))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Officer not found'}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Officer deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# File serving route
@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    try:
        return send_from_directory('uploads', filename)
    except Exception as e:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)
