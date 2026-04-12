import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import socket
import json
import datetime
import secrets
import pytz

def get_ireland_time():
    return datetime.datetime.now(pytz.timezone('Europe/Dublin'))
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, ActivityLog

COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria",
    "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
    "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia",
    "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica",
    "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt",
    "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon",
    "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel",
    "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Korea, North", "Korea, South", "Kosovo",
    "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania",
    "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius",
    "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia",
    "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Macedonia", "Norway", "Oman",
    "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
    "Qatar", "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe",
    "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia",
    "South Africa", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan",
    "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City",
    "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
]

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-abac'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Email config
EMAIL_ADDRESS = "mirza.arslan@unitedcdlschool.com"
EMAIL_PASSWORD = "jhsc zinv qogw vzdl"

import threading

def send_email(to_email, subject, body):
    def send_async():
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Use SSL on port 465 to bypass common ISP blocks on port 587
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_ADDRESS, to_email, text)
            server.quit()
            print(f"Email successfully sent to {to_email}")
        except Exception as e:
            print(f"Error sending email async: {e}")
            
    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()

def notify_monitor(alert_type, user, additional_data=None):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 9999))
        
        data = {
            'type': alert_type,
            'username': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'location': request.form.get('location', 'Unknown'),
            'timestamp': get_ireland_time().strftime("%Y-%m-%d %H:%M:%S")
        }
        if additional_data:
            data.update(additional_data)
            
        sock.sendall(json.dumps(data).encode())
        sock.close()
    except ConnectionRefusedError:
        print("Monitor server is not running.")
    except Exception as e:
        print(f"TCP Client Error: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return login() # Call the existing login function to handle the POST logic
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            if user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
    return render_template('login.html', countries=COUNTRIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        location = request.form.get('location', '').strip()
        device = request.headers.get('User-Agent', 'Unknown Device')
        
        if not location:
            flash('Login blocked: Geolocation constraints could not be verified. Location is empty.', 'danger')
            return render_template('login.html', countries=COUNTRIES)
            
        user = User.query.filter_by(email=email).first()
        
        if user:
            if not user.is_approved:
                flash('Your account is pending admin approval.', 'warning')
                return render_template('login.html', countries=COUNTRIES)
                
            if user.is_locked:
                notify_monitor('ALERT: ACCOUNT LOCKED - ADMIN RELEASE PENDING', user, {
                    'failed_attempts': user.failed_attempts,
                    'account_locked': 'Yes',
                    'lockout_timestamp': str(user.lockout_timestamp)
                })
                flash('Your account is locked. Please contact admin.', 'danger')
                return render_template('login.html', countries=COUNTRIES)
            
            # Identify mismatches
            location_failed = user.location != '*' and user.location.lower() != location.lower()
            password_failed = not check_password_hash(user.password, password)
            
            if location_failed or password_failed:
                if password_failed:
                    user.failed_attempts += 1
                    db.session.commit()
                    
                    if user.failed_attempts == 3:
                        notify_monitor('ALERT: MULTIPLE FAILED LOGIN ATTEMPTS', user, {
                            'failed_attempts': 3,
                            'account_locked': 'No'
                        })
                        send_email(user.email, 'Security Warning', '3 failed login attempts detected on your account.')
                        flash('Warning: 3 failed attempts. 1 attempt left before lockout.', 'warning')
                        log = ActivityLog(user_id=user.id, action="ALERT: MULTIPLE FAILED LOGINS DETECTED", device=device, location=location)
                        db.session.add(log)
                        db.session.commit()
                        return render_template('login.html', countries=COUNTRIES)
                    elif user.failed_attempts >= 4:
                        user.is_locked = True
                        user.lockout_timestamp = get_ireland_time()
                        db.session.commit()
                        
                        notify_monitor('ALERT: USER ACCOUNT LOCKED', user, {
                            'failed_attempts': user.failed_attempts,
                            'account_locked': 'Yes',
                            'lockout_timestamp': str(user.lockout_timestamp)
                        })
                        
                        send_email(user.email, 'Account Locked', 'Your account has been locked. Contact Admin.')
                        send_email(EMAIL_ADDRESS, 'User Locked Out', f'User {user.email} has been locked out after 4 attempts.')
                        
                        log = ActivityLog(user_id=user.id, action="ALERT: USER ACCOUNT LOCKED OUT", device=device, location=location)
                        db.session.add(log)
                        db.session.commit()

                        flash('Account locked. Contact your admin for unlock.', 'danger')
                        return render_template('login.html', countries=COUNTRIES)
                    else:
                        flash('Invalid credentials, please try again.', 'danger')
                        return render_template('login.html', countries=COUNTRIES)

                if location_failed:
                    notify_monitor('ALERT: UNKNOWN LOGIN LOCATION IDENTIFIED', user)
                    log = ActivityLog(user_id=user.id, action="ALERT: UNKNOWN LOGIN LOCATION IDENTIFIED", device=device, location=location)
                    db.session.add(log)
                    db.session.commit()
                    
                flash('Invalid credentials, please try again.', 'danger')
                return render_template('login.html', countries=COUNTRIES)
            
            # Success
            user.failed_attempts = 0
            
            log = ActivityLog(user_id=user.id, action="Successful Login", device=device, location=location)
            db.session.add(log)
            db.session.commit()
            
            session['user_id'] = user.id
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            return redirect(url_for('index'))
        else:
            flash('User not found.', 'danger')

    return render_template('login.html', countries=COUNTRIES)

@app.route('/logout')
def logout():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.force_logout = False
            db.session.commit()
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role != 'Admin': return redirect(url_for('index'))
    
    users = User.query.all()
    # Fetch all global activity logs for the security monitor
    activities = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return render_template('admin_dashboard.html', user=user, users=users, activities=activities)

@app.route('/admin/unlock/<int:id>', methods=['POST'])
def unlock_user(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    admin = User.query.get(session['user_id'])
    if admin.role != 'Admin': return redirect(url_for('index'))
    
    user = User.query.get(id)
    if user:
        user.is_locked = False
        user.failed_attempts = 0
        user.lockout_timestamp = None
        db.session.commit()
        
        log = ActivityLog(user_id=user.id, action="Account Unlocked by Admin", device="Admin Panel", location=admin.location)
        db.session.add(log)
        db.session.commit()
        
        send_email(user.email, 'Account Unlocked', 'Your account has been unlocked by the admin.')
        flash(f'User {user.email} unlocked.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve/<int:id>', methods=['POST'])
def approve_user(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    admin = User.query.get(session['user_id'])
    if admin.role != 'Admin': return redirect(url_for('index'))
    
    user = User.query.get(id)
    if user:
        user.is_approved = True
        
        # Generate secure temp password on approval
        raw_password = secrets.token_urlsafe(8)
        user.password = generate_password_hash(raw_password, method='pbkdf2:sha256')
        db.session.commit()
        
        log = ActivityLog(user_id=user.id, action="Account Approved & Password Generated", device="Admin Panel", location=admin.location)
        db.session.add(log)
        db.session.commit()
        
        email_body = f"Hello {user.first_name},\n\nYour account has been approved by the admin.\n\nYour temporary password is: {raw_password}\n\nPlease change it immediately upon logging in for the first time."
        send_email(user.email, 'Account Approved - Welcome', email_body)
        
        print(f"DEBUG - Auto Generated Password for {user.email}: {raw_password}") # Terminal fallback for testing
        
        flash(f'User {user.email} approved and temporary password emailed.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/decline/<int:id>', methods=['POST'])
def decline_user(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    admin = User.query.get(session['user_id'])
    if admin.role != 'Admin': return redirect(url_for('index'))
    
    user = User.query.get(id)
    if user:
        # Erase their logs so we don't hit foreign key conflicts when deleting the user
        ActivityLog.query.filter_by(user_id=user.id).delete()
        user_email = user.email
        db.session.delete(user)
        
        log = ActivityLog(user_id=admin.id, action=f"Declined & Deleted Request: {user_email}", device="Admin Panel", location=admin.location)
        db.session.add(log)
        db.session.commit()
        
        # We can send them an email
        send_email(user_email, 'Account Declined', 'Your request for an employee portal account has been reviewed and declined by the Security Administrator.')
        
        flash(f'Request for {user_email} declined and pending account deleted.', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/view_employee/<int:id>', methods=['GET'])
def view_employee(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    admin = User.query.get(session['user_id'])
    if admin.role != 'Admin': return redirect(url_for('index'))
    
    emp = User.query.get_or_404(id)
    activities = ActivityLog.query.filter_by(user_id=emp.id).order_by(ActivityLog.timestamp.desc()).all()
    return render_template('admin_view_employee.html', emp=emp, activities=activities)

@app.route('/user', methods=['GET'])
def user_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    # Redirect to change password if they are using their autogenerated password!
    if user.is_first_login:
        flash('You must change your autogenerated password to continue.', 'warning')
        return redirect(url_for('change_password'))
        
    activities = ActivityLog.query.filter_by(user_id=user.id).order_by(ActivityLog.timestamp.desc()).limit(15).all()
    return render_template('user_dashboard.html', user=user, activities=activities)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        mobile = request.form['mobile']
        department = request.form['department']
        access_required = request.form['access_required']
        location = request.form['location']
        job_title = request.form['job_title']
        payroll = request.form['payroll']
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('signup'))
        
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            mobile=mobile,
            department=department,
            access_required=access_required,
            location=location,
            job_title=job_title,
            payroll=payroll,
            password=None,
            is_first_login=True,
            is_approved=False
        )
        db.session.add(new_user)
        db.session.commit()
        
        log = ActivityLog(user_id=new_user.id, action="Onboarding Completed (Pending Admin Approval)", device="System", location=location)
        db.session.add(log)
        db.session.commit()
        
        flash('Account Created Successfully! Your application is pending admin approval. You will receive an email once approved.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html', countries=COUNTRIES)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        new_pw = request.form['password']
        user.password = generate_password_hash(new_pw, method='pbkdf2:sha256')
        user.is_first_login = False
        db.session.commit()
        
        log = ActivityLog(user_id=user.id, action="Password Successfully Changed", device=request.headers.get('User-Agent', 'Unknown Device'), location="System")
        db.session.add(log)
        db.session.commit()
        
        flash('Password updated! Welcome to the portal.', 'success')
        return redirect(url_for('user_dashboard'))
        
    return render_template('change_password.html')

def setup_db():
    with app.app_context():
        db.create_all()
        # Ensure a default admin account exists
        if not User.query.filter_by(role='Admin').first():
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin = User(
                first_name='System',
                last_name='Admin',
                email='admin@abac.com',
                mobile='0000000000',
                location='Dubai',
                password=hashed_pw,
                role='Admin',
                is_approved=True
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    setup_db()
    app.run(debug=True, port=5001)
