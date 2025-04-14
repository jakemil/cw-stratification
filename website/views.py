from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import time
from flask import session, render_template_string
from werkzeug.http import quote_etag

from .models import Note, Info, Stratification, User, Feedback, Supervisor_Notes, Performance
from . import db

views = Blueprint('views', __name__)

@views.route('/export-staff-comparison-history', methods=['GET'])
def export_staff_comparison_history():
    """
    Standalone route to display each user's last name, first name,
    and the number of items in their staff_comparison_history.
    """
    # Query all users
    users = User.query.all()
    output_lines = []

    for user in users:
        # Check if the user has a related Performance entry
        performance = Performance.query.filter_by(user_id=user.id).first()

        # Get the number of items in staff_comparison_history, or 0 if not available
        if performance and performance.staff_comparison_history:
            num_of_items = len(performance.staff_comparison_history)
        else:
            num_of_items = 0

        # Construct the output line for the user
        output_lines.append(f"{user.last_name}, {user.first_name}: {num_of_items}")

    # Generate a simple HTML page to render the results
    html_template = """
    <html>
        <head>
            <title>Export Staff Comparison History</title>
        </head>
        <body>
            <h1>Staff Comparison History</h1>
            <pre>
{{ output_content }}
            </pre>
        </body>
    </html>
    """

    # Render the output as plain text in the browser
    return render_template_string(html_template, output_content="\n".join(output_lines))



@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        note = request.form.get('note') # Gets the note from the HTML
        supervisor_note = request.form.get('supervisor_note')
        submit_type = request.form.get("submit_type")
        # Check which button was pressed
        if submit_type == "user_note":
            existing_notes = Note.query.filter_by(user_id=current_user.id).all()
            if existing_notes:
                # Call the delete_note logic
                for existing_note in existing_notes:
                    db.session.delete(existing_note)
                db.session.commit()
                flash('Previous narrative deleted. Submitting Updated n=Narrative.', category='success')
            elif len(note) < 1:
                flash('Narrative is too short!', category='error')
            elif len(note) > 1300:
                flash('Narrative is too long! (>=1500)', category='error')
            else:
                flash('Narrative submitted!', category='success')
            new_note = Note(data=note, user_id=current_user.id)  # Provide the schema for the note
            db.session.add(new_note)  # Add the note to the database
            db.session.commit()

        # Check which button was pressed
        elif submit_type == "supervisor_note":
            existing_notes = Supervisor_Notes.query.filter_by(user_id=current_user.id).all()
            if existing_notes:
                # Call the delete_note logic
                for existing_note in existing_notes:
                    db.session.delete(existing_note)
                db.session.commit()
                flash('Previous Supervisor Note deleted. Submitting Updated Evaluation.', category='success')
            elif len(supervisor_note) < 1:
                flash('Evaluation is too short!', category='error')
            elif len(supervisor_note) > 300:
                flash('Evaluation is too long! (>=200)', category='error')
            else:
                flash('Evaluation submitted!', category='success')
            new_note = Supervisor_Notes(data=supervisor_note, user_id=current_user.id)  # Provide the schema for the note
            db.session.add(new_note)  # Add the note to the database
            db.session.commit()

    return render_template("home.html", user=current_user)

@views.route('/select-phase', methods=['GET', 'POST'])
@login_required
def select_phase():
    return render_template("select_phase.html", user=current_user)

@views.route('/select-query', methods=['GET', 'POST'])
@login_required
def select_query():
    return render_template("select_query.html", user=current_user)

@views.route('/staff-performance', methods=['GET', 'POST'])
@login_required
def staff_performance():
    user_info = Info.query.filter_by(user_id=current_user.id).first()
    if not user_info:
        flash('User info missing.', category='error')
        return redirect(url_for('views.info'))

    current_flight = user_info.flight
    current_class_year = user_info.class_year

    # Get all users in the flight (excluding self)
    users_in_flight = Info.query.filter_by(flight=current_flight).all()
    user_ids_in_flight = [info.user_id for info in users_in_flight if info.user_id != current_user.id]
    info_by_id = {info.user_id: info for info in users_in_flight}

    user_performance = Performance.query.filter_by(user_id=current_user.id).first()
    if not user_performance:
        user_performance = Performance(user_id=current_user.id, staff_comparison_history=[])
        db.session.add(user_performance)
        db.session.commit()

    comparison_history = user_performance.staff_comparison_history or []

    # Determine eligible users
    eligible_users = []
    for uid in user_ids_in_flight:
        if uid in comparison_history:
            continue
        other_info = info_by_id.get(uid)
        if current_class_year in [2027, 2028] and other_info.class_year == current_class_year:
            continue
        eligible_users.append(uid)

    if not eligible_users:
        flash("No more users available for comparison.", category="warning")
        return redirect(url_for('views.select_query'))

    # 🧠 blah Only pick a new user if reset_user flag is set, no one selected yet, or when navigating back
    if 'selected_user_id' not in session or session.get('reset_user') or request.method == 'GET':
        session['selected_user_id'] = random.choice(eligible_users)
        session.pop('reset_user', None)

    selected_user_id = session['selected_user_id']
    selected_user = User.query.get(selected_user_id)
    eligible_user_details = User.query.filter(User.id.in_(eligible_users)).all()

    print("the selected user id is:")
    print(selected_user_id)
    print("the selected user name is:")
    print(selected_user.last_name)

    if request.method == 'POST':
        score = request.form.get('score')
        if not score or not score.isdigit() or not (0 <= int(score) <= 25):
            flash('Invalid score. Must be 0–25.', category='error')
            return render_template('staff_performance.html', selected_user=selected_user,
                                   eligible_users=eligible_user_details, user=current_user)

        score = int(score)

        selected_perf = Performance.query.filter_by(user_id=selected_user_id).first()
        if not selected_perf:
            selected_perf = Performance(
                user_id=selected_user_id,
                num_squad_comparisons=0,
                question_1=0, question_1_total=0,
                question_2=0, question_3=0, question_4=0, question_5=0,
                question_6=0, question_7=0, question_8=0, question_9=0, question_10=0,
                overall_score=0, staff_comparison_history=[]
            )
            db.session.add(selected_perf)

        selected_perf.question_1 = (selected_perf.question_1 or 0) + score
        selected_perf.question_1_total = (selected_perf.question_1_total or 0) + 1

        # Update history
        if selected_user_id not in comparison_history:
            comparison_history.append(selected_user_id)
            user_performance.staff_comparison_history = list(comparison_history)

        selected_perf.overall_score = update_total_score(selected_perf)

        # ✅ Set the reset flag so GET will pick a new user
        session['reset_user'] = True
        db.session.commit()

        flash('Score submitted!', category='success')
        return redirect(url_for('views.staff_performance'))

    return render_template(
        'staff_performance.html',
        selected_user=selected_user,
        eligible_users=eligible_user_details,
        user=current_user
    )



@views.route('/squad-performance', methods=['GET', 'POST'])
@login_required
def squad_performance():
    # Step 1: Get the current user's squadron
    user_info = Info.query.filter_by(user_id=current_user.id).first()
    if not user_info:
        flash('User information is not available. Please complete your profile.', category='error')
        return redirect(url_for('views.info'))  # Redirect to the info page if the user's info is missing

    current_squadron = user_info.squadron  # Get the current user's squadron

    # Step 2: Retrieve all users from the same squadron
    all_squadron_users = Info.query.filter_by(squadron=current_squadron).all()
    if not all_squadron_users:
        flash('No users found in your squadron.', category='error')
        return redirect(url_for('views.home'))

    # Step 3: Retrieve each user's num_squad_comparisons
    users_with_comparisons = []
    for user_info in all_squadron_users:
        user = User.query.get(user_info.user_id)  # Get the User object
        performance = Performance.query.filter_by(user_id=user.id).first()

        if not performance:
            # Initialize a Performance entry for users with no entry
            performance = Performance(user_id=user.id, num_squad_comparisons=0, question_1=0,
                                      question_1_total=0, question_2=0, question_3=0,
                                      question_4=0, question_5=0, question_6=0, question_7=0,
                                      question_8=0, question_9=0, question_10=0, overall_score=0,
                                      staff_comparison_history=[])
            db.session.add(performance)
            db.session.commit()  # Save the changes to the database

        # Add a filter to skip the current user
        if user.id == current_user.id:
            continue
        users_with_comparisons.append((user, performance.num_squad_comparisons))

    # Step 4: Find users with the least number of comparisons
    min_comparisons = min([comp[1] for comp in users_with_comparisons])  # Find the lowest num_squad_comparisons
    eligible_users = [comp[0] for comp in users_with_comparisons if comp[1] == min_comparisons]

    # 🧠 Implement the reset flag technique for selecting the user
    if 'selected_user_id' not in session or session.get('reset_user'):
        # Use time as the seed and choose randomly if there are ties
        random.seed(time.time())
        selected_user = random.choice(eligible_users)  # Randomly select the user
        session['selected_user_id'] = selected_user.id
        session.pop('reset_user', None)  # Reset the flag
    else:
        selected_user_id = session['selected_user_id']
        selected_user = User.query.get(selected_user_id)

    if request.method == 'POST':
        # Process POST request: Collect answers to questions
        questions = {
            "question_2": request.form.get("question_2"),
            "question_3": request.form.get("question_3"),
            "question_4": request.form.get("question_4"),
            "question_5": request.form.get("question_5"),
            "question_6": request.form.get("question_6"),
            "question_7": request.form.get("question_7"),
            "question_8": request.form.get("question_8"),
            "question_9": request.form.get("question_9"),
            "question_10": request.form.get("question_10"),
        }

        # Update the Performance record for the selected user
        selected_user_performance = Performance.query.filter_by(user_id=selected_user.id).first()
        for question, response in questions.items():
            if response == 'yes':
                current_value = getattr(selected_user_performance, question) or 0
                setattr(selected_user_performance, question, current_value + 1)

        # Increment num_squad_comparisons
        selected_user_performance.num_squad_comparisons += 1
        selected_user_performance.overall_score = update_total_score(selected_user_performance)
        print(selected_user_performance.overall_score)

        # ✅ Set the reset flag so a new user is selected on the next GET
        session['reset_user'] = True
        db.session.commit()

        flash('Squad performance review submitted successfully!', category='success')
        return redirect(url_for('views.squad_performance'))

    # Access note and supervisor note data
    user_notes = selected_user.notes  # This will return a list of Note objects
    supervisor_notes = selected_user.supervisor_notes  # This will return a list of SupervisorNotes objects
    note_data = user_notes[0].data if user_notes else "No notes available"
    supervisor_note_data = supervisor_notes[0].data if supervisor_notes else "No supervisor notes available"

    # Render the template with the selected user's information
    return render_template(
        'squad_performance.html',
        selected_user=selected_user,
        user=current_user,
        note_data=note_data,
        supervisor_note_data=supervisor_note_data
    )


@views.route('/info', methods=['GET', 'POST'])
@login_required
def info():

    if request.method == 'POST':
        group = request.form.get('group')  # Gets the cadet group (integer)
        squadron = request.form.get('squadron')  # Gets the cadet squadron (integer)
        flight = request.form.get('flight-staff')  # Gets the flight/staff
        class_year = request.form.get('class-year')  # Gets the class year input
        admin_password = request.form.get('admin-password')  # Gets the admin password

        # Squadron-specific passwords
        squadron_passwords = {i: f"CS{i:02d}_password" for i in range(1, 41)}

        admin = None

        # Validation
        if not group or not squadron or not flight:
            flash('All fields except admin password are required!', category='error')
        elif admin_password:
            # Check admin password if provided
            correct_password = squadron_passwords.get(int(squadron))
            if correct_password and admin_password == correct_password:
                admin = squadron  # Grant admin rights
                flash(f'Admin rights granted for Cadet Squadron {squadron}!', category='success')
            else:
                flash('Invalid admin password!', category='error')
        else:
            admin = None  # No admin rights provided if no password entered

        if admin is not None or not admin_password:
            # Check if an entry already exists for the current user
            existing_info = Info.query.filter_by(user_id=current_user.id).first()

            if existing_info:
                # Update existing entry
                existing_info.group = group
                existing_info.squadron = squadron
                existing_info.flight = flight
                existing_info.admin = admin
                flash('Information updated successfully! Now Navigate to Narrative Page', category='success')
            else:
                # Create a new entry
                new_info = Info(
                    group=group,
                    squadron=squadron,
                    flight=flight,
                    admin=admin,
                    class_year=class_year,
                    user_id=current_user.id
                )
                new_strat = Stratification(
                    user_id=current_user.id,
                    overall_elo=1000,
                    duty_perform_elo=1000,
                    professionalism_elo=1000,
                    num_comparisons=0,
                    leadership_elo=1000,
                    character_elo=1000,
                )
                db.session.add(new_strat)
                db.session.add(new_info)
                flash('Information added successfully! Now Navigate to Narrative Page', category='success')

            db.session.commit()

    # Retrieve the existing info to display in the form
    user_info = Info.query.filter_by(user_id=current_user.id).first()

    return render_template(
        "info.html",
        user=current_user,
        info=user_info
    )


@views.route('/admin-dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    # Get the class year filter from query parameters
    class_year = request.args.get('class_year', type=int)

    # Query for users in the admin's squadron
    admin_info = Info.query.filter_by(user_id=current_user.id).first()
    if not admin_info:  # Ensure the current user is an admin
        return "Unauthorized Access", 403

    query = db.session.query(
        User.first_name,
        User.last_name,
        Performance.overall_score,
        Stratification.overall_elo,
        Stratification.duty_perform_elo,
        Stratification.professionalism_elo,
        Stratification.leadership_elo,
        Stratification.character_elo,
        Note.data.label("note_data"),
        Supervisor_Notes.data.label("supervisor_data")
    ).join(Info, User.id == Info.user_id) \
        .join(Performance, User.id == Performance.user_id, isouter=True) \
        .join(Stratification, User.id == Stratification.user_id, isouter=True) \
        .join(Note, User.id == Note.user_id, isouter=True) \
        .join(Supervisor_Notes, User.id == Supervisor_Notes.user_id, isouter=True) \
        .filter(Info.squadron == admin_info.squadron)

    print(class_year)
    if class_year:
        query = query.filter(Info.class_year == class_year)

    users = query.order_by(Performance.overall_score.desc().nullslast(), User.last_name, User.first_name).all()

    return render_template("admin_dashboard.html", users=users, squadron=admin_info.squadron, class_year=class_year)


@views.route('/phase-two', methods=['GET', 'POST'])
@login_required
def phase_two():
    class_year = request.args.get('class_year', type=int)
    selected_user_id = request.args.get('selected_user', type=int)
    action = request.form.get('action')
    page = request.args.get('page', 1, type=int)

    admin_info = Info.query.filter_by(user_id=current_user.id).first()
    if not admin_info:
        return "Unauthorized Access", 403

    # Get distinct class years for the dropdown
    class_years = [row[0] for row in db.session.query(Info.class_year).distinct().order_by(Info.class_year.asc()).all()]

    query = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        Performance.overall_score,
        Stratification.overall_elo,
        Note.data.label("note_data"),
        Supervisor_Notes.data.label("supervisor_data")
    ).join(Info, User.id == Info.user_id) \
        .join(Performance, User.id == Performance.user_id, isouter=True) \
        .join(Stratification, User.id == Stratification.user_id, isouter=True) \
        .join(Note, User.id == Note.user_id, isouter=True) \
        .join(Supervisor_Notes, User.id == Supervisor_Notes.user_id, isouter=True) \
        .filter(Info.squadron == admin_info.squadron)

    if class_year:
        query = query.filter(Info.class_year == class_year)

    query = query.order_by(Performance.overall_score.desc().nullslast(), User.last_name, User.first_name)
    users_paginated = query.paginate(page=page, error_out=False)
    users = users_paginated.items
    all_users = query.all()

    selected_user = None
    above_user = None
    below_user = None

    if selected_user_id:
        user_index = next((i for i, u in enumerate(all_users) if u.id == selected_user_id), None)
        if user_index is not None:
            selected_user = all_users[user_index]
            if user_index > 0:
                above_user = all_users[user_index - 1]
            if user_index < len(all_users) - 1:
                below_user = all_users[user_index + 1]

            if action == "move_up" and above_user:
                swap_scores(selected_user.id, above_user.id, action)
                return redirect(url_for('views.phase_two', class_year=class_year, selected_user=selected_user_id))
            elif action == "move_down" and below_user:
                swap_scores(selected_user.id, below_user.id, action)
                return redirect(url_for('views.phase_two', class_year=class_year, selected_user=selected_user_id))

    if request.method == 'POST':
        # save feedback
        feedback = request.form.get('feedback', None)  # Feedback for User1

        try:
            # Save feedback for user1
            if feedback:
                new_feedback = Feedback(
                    admin_feedback=feedback,  # Optional duplicate if needed
                    user_id=selected_user_id  # Use winner_id for User1 (logic can differ if needed)
                )
                db.session.add(new_feedback)

            db.session.commit()  # Commit all changes to the database

            # Flash success message and redirect
            flash('Feedback submitted successfully!', 'success')

        except Exception as e:
            db.session.rollback()  # Rollback transaction on error
            flash(f'Error submitting feedback: {str(e)}', 'danger')

    return render_template(
        "phase_two.html",
        users=users,
        selected_user=selected_user,
        above_user=above_user,
        below_user=below_user,
        class_year=class_year,
        class_years=class_years,
        pagination=users_paginated
    )

def swap_scores(user1_id, user2_id, action):
    """ Swaps the ELO scores between two users. """
    user1 = Performance.query.filter_by(user_id=user1_id).first()
    user2 = Performance.query.filter_by(user_id=user2_id).first()

    if user1 and user2:
        if action == "move_up":
            user1.overall_score, user2.overall_score = (user2.overall_score+1), user1.overall_score
        else:
            user1.overall_score, user2.overall_score = (user2.overall_score-1), user1.overall_score
        db.session.commit()


def swap_elos(user1_id, user2_id, action):
    """ Swaps the ELO scores between two users. """
    user1 = Stratification.query.filter_by(user_id=user1_id).first()
    user2 = Stratification.query.filter_by(user_id=user2_id).first()

    if user1 and user2:
        if action == "move_up":
            user1.overall_elo, user2.overall_elo = (user2.overall_elo+1), user1.overall_elo
        else:
            user1.overall_elo, user2.overall_elo = (user2.overall_elo-1), user1.overall_elo
        db.session.commit()


@views.route('/strat-users', methods=['GET', 'POST'])
@login_required
def strat_users():
    # Get the current admin's squadron info
    admin_info = Info.query.filter_by(user_id=current_user.id).first()
    if not admin_info:
        return "Unauthorized Access", 403  # Ensure the current user is an admin

    # Get the class year from query parameters
    class_year = request.args.get('class_year', type=int)

    if not class_year:
        # If no class year is selected, provide a dropdown for selection
        class_years = db.session.query(Info.class_year).distinct().all()
        return render_template('strat_users.html', class_years=[cy[0] for cy in class_years], users=None)

    # Query for users in the same squadron and class year (including those without notes or supervisor notes)
    users = db.session.query(
        User,
        Note.data.label("narrative_data"),  # Make sure narrative (data) can be NULL
        Supervisor_Notes.data.label("supervisor_data"),  # Supervisor notes can also be NULL
        Stratification
    ).join(Info, Info.user_id == User.id) \
        .outerjoin(Note, Note.user_id == User.id) \
        .outerjoin(Supervisor_Notes, Supervisor_Notes.user_id == User.id) \
        .outerjoin(Stratification, Stratification.user_id == User.id) \
        .filter(Info.squadron == admin_info.squadron) \
        .filter(Info.class_year == class_year).all()

    if not users:
        flash(f"No users found for class year {class_year} in squadron {admin_info.squadron}.", category='error')
        return redirect(url_for('views.strat_users'))

    #check to ensure database is set up with comparison count
    for user in users:
        # Query the Stratification entry for the user
        test = db.session.query(Stratification).filter_by(user_id=user[0].id).first()

        # Check if the entry exists and if num_comparisons is None
        if test and test.num_comparisons is None:
            print("Changing num_comparisons from None to 0")

            # Update the value of num_comparisons
            test.num_comparisons = 0

            # Commit the change
            db.session.commit()

    if request.method == 'POST':
        # Handle ranking update based on form submission
        winner_id = int(request.form['winner'])
        loser_id = int(request.form['loser'])

        # save feedback
        user1_feedback = request.form.get('user1_feedback', None)  # Feedback for User1
        user2_feedback = request.form.get('user2_feedback', None)  # Feedback for User2

        try:
            # Save feedback for user1
            if user1_feedback:
                new_feedback_user1 = Feedback(
                    admin_feedback=user1_feedback,  # Optional duplicate if needed
                    user_id=winner_id  # Use winner_id for User1 (logic can differ if needed)
                )
                db.session.add(new_feedback_user1)

            # Save feedback for user2
            if user2_feedback:
                new_feedback_user2 = Feedback(
                    admin_feedback=user2_feedback,
                    user_id=loser_id  # Use loser_id for User2 (logic can differ)
                )
                db.session.add(new_feedback_user2)

            db.session.commit()  # Commit all changes to the database

            # Flash success message and redirect
            flash('Feedback submitted successfully!', 'success')

        except Exception as e:
            db.session.rollback()  # Rollback transaction on error
            flash(f'Error submitting feedback: {str(e)}', 'danger')

        # Update all ELO rankings
        winner = Stratification.query.filter_by(user_id=winner_id).first()
        loser = Stratification.query.filter_by(user_id=loser_id).first()

        #uncomment if you want criteria
        #criteria_list = ['overall', 'duty_performance', 'professionalism', 'leadership', 'character']
        criteria_list = ['overall']

        # Ensure 'overall' is required
        overall_winner = request.form.get('overall_winner')
        if not overall_winner:
            flash('The "overall" criterion is required.', category='error')
            return redirect(request.url)  # Redirect back if overall is missing

        # Process the overall criterion
        if overall_winner == 'winner':
            update_elo(winner, loser, 'overall')
        elif overall_winner == 'loser':
            update_elo(loser, winner, 'overall')

        # Process optional criteria
        for criterion in criteria_list[1:]:  # Skip 'overall'
            criterion_winner = request.form.get(f'{criterion}_winner')
            if criterion_winner == 'winner':
                update_elo(winner, loser, criterion)
            elif criterion_winner == 'loser':
                update_elo(loser, winner, criterion)
            # If no input is provided for this criterion, skip it

        db.session.commit()

    user1, user2 = select_users(users)
    return render_template(
        'strat_users.html',
        class_year=class_year,
        user1=user1,
        user2=user2,
        users=users
    )


import random

# Create a set to store pairs already compared
compared_pairs = set()


def select_users(users):
    """
    Selects two users for comparison based on the nearest neighbor in terms of ELO.
    Avoids repeating comparisons using the `comparison_history` field.
    Updates num_comparisons and records comparison history.
    """
    # Create a list of tuples (User, Note, Stratification)
    user_entries = [
        (user, strat) for user, strat in [
            (user, db.session.query(Stratification).filter_by(user_id=user[0].id).first())
            for user in users
        ]
        if strat and strat.num_comparisons is not None
    ]

    # Debug: Print all users and their comparison histories
    print("\n--- Current Users and Their States ---")
    for user, strat in user_entries:
        print(
            f"User ID: {user[0].id}, "
            f"First Name: {user[0].first_name}, "
            f"Overall ELO: {strat.overall_elo}, "
            f"Num Comparisons: {strat.num_comparisons}, "
            f"Comparison History: {strat.comparison_history}"
        )
    print("--------------------------------------\n")

    # Sort the list by num_comparisons in ascending order
    user_entries.sort(key=lambda x: x[1].num_comparisons)

    # Nearest neighbor selection
    for i, (user1, strat1) in enumerate(user_entries):
        nearest_neighbor = None
        smallest_elo_diff = float('inf')

        for user2, strat2 in user_entries:
            if user1[0].id == user2[0].id:
                continue  # Skip self-comparison
            if user2[0].id in strat1.comparison_history:
                continue  # Skip if already compared

            elo_diff = abs(strat1.overall_elo - strat2.overall_elo)
            if elo_diff < smallest_elo_diff:
                smallest_elo_diff = elo_diff
                nearest_neighbor = (user2, strat2)

        if nearest_neighbor:
            user2, strat2 = nearest_neighbor

            # Update num_comparisons
            strat1.num_comparisons += 1
            strat2.num_comparisons += 1

            # Update comparison history
            strat1.comparison_history.append(user2[0].id)
            strat2.comparison_history.append(user1[0].id)

            # Commit the changes to the database
            db.session.commit()

            # Debug: Print selected users and their updates
            print(
                f"Selected User1: {user1[0].id} (ELO: {strat1.overall_elo}, Comparison History: {strat1.comparison_history})")
            print(
                f"Selected User2: {user2[0].id} (ELO: {strat2.overall_elo}, Comparison History: {strat2.comparison_history})")

            return user1, user2

    # Fallback: Random selection if no nearest neighbor is available
    user1, user2 = random.sample(users, 2)
    print("Fallback to random selection")
    return user1, user2


def update_elo(winner, loser, criterion, k=32):
    # Define the ELO fields for each criterion
    elo_fields = {
        'overall': 'overall_elo',
        'duty_performance': 'duty_perform_elo',
        'professionalism': 'professionalism_elo',
        'leadership': 'leadership_elo',
        'character': 'character_elo'
    }

    if criterion not in elo_fields:
        raise ValueError("Invalid criterion for ELO update.")

    # Get the ELO fields
    winner_field = getattr(winner, elo_fields[criterion])
    loser_field = getattr(loser, elo_fields[criterion])

    # Calculate expected scores
    expected_winner = 1 / (1 + 10 ** ((loser_field - winner_field) / 400))
    expected_loser = 1 - expected_winner

    # Update scores (check to see if I am loser, if so, make winner calculation)
    # user_num = getattr(loser, "user_id")
    # user = User.query.filter_by(id=user_num).first()
    # first_name = user.first_name
    # last_name = user.last_name
    # if first_name == "Jake" and last_name == "Miller":
    # setattr(winner, elo_fields[criterion], int(winner_field + k * (0 - expected_loser)))
    # setattr(loser, elo_fields[criterion], int(loser_field + k * (1 - expected_winner)))
    # else:
    setattr(winner, elo_fields[criterion], int(winner_field + k * (1 - expected_winner)))
    setattr(loser, elo_fields[criterion], int(loser_field + k * (0 - expected_loser)))


@views.route('/metrics', methods=['GET'])
@login_required
def metrics():
    # Get the current user's Info entry (to determine squadron and class year)
    current_user_info = Info.query.filter_by(user_id=current_user.id).first()
    feedbacks = Feedback.query.filter_by(user_id=current_user.id).filter(Feedback.admin_feedback.isnot(None)).all()

    # Send feedback as a plain list of strings making it able to convert to JSON
    feedback_texts = [fb.admin_feedback for fb in feedbacks]
    if not current_user_info:
        flash("User information not found.", category="error")
        return redirect(url_for('views.home'))

    # Get class year and squadron of current user
    class_year = current_user_info.class_year
    squadron = current_user_info.squadron

    # Query all users in the same squadron and class year
    users = db.session.query(User, Stratification).join(Info, User.id == Info.user_id) \
        .join(Stratification, User.id == Stratification.user_id) \
        .filter(Info.squadron == squadron, Info.class_year == class_year).all()

    # Calculate rankings for all categories
    categories = ['overall_elo', 'duty_perform_elo', 'professionalism_elo', 'leadership_elo', 'character_elo']
    rankings = {}

    for category in categories:
        # Sort users based on the current category in descending order
        sorted_users = sorted(users, key=lambda u: getattr(u[1], category), reverse=True)

        # Find the rank of the current user
        for rank, user in enumerate(sorted_users, start=1):
            if user[0].id == current_user.id:
                rankings[category] = f"{rank}/{len(sorted_users)}"
                break

    # Render the template with the rankings
    return render_template(
        "metrics.html",
        rankings=rankings,
        category_labels=['Overall', 'Duty Performance', 'Professionalism', 'Leadership', 'Character'],
        feedbacks=feedback_texts
    )


def update_total_score(performance):
    """
    Calculate and update the overall score for a given Performance record.

    Parameters:
        performance (Performance): A Performance object containing response data for all questions (1-10).

    Behavior:
        - Averages JSON values for question_one (0-20 scale) directly.
        - Averages JSON values for questions two through ten (binary 0/1 values).
        - Applies weighted percentages to each question's score.
        - Updates the overall_score field in the Performance object.

    Returns:
        float: The calculated overall score.
    """
    if not performance:
        return None  # Exit early if no performance object exists

    # Define weights for each question:
    weights = {
        "question_1": 0.25,  # 25%
        "question_2": 0.1563,  # 15.63%
        "question_3": 0.1198,  # 11.98%
        "question_4": 0.1146,  # 11.46%
        "question_5": 0.1094,  # 10.94%
        "question_6": 0.1042,  # 10.42%
        "question_7": 0.0573,  # 5.73%
        "question_8": 0.0521,  # 5.21%
        "question_9": 0.0208,  # 2.08%
        "question_10": 0.0156  # 1.56%
    }

    # Calculate weighted scores for each question
    weighted_scores = {}

    # Question one is averaged directly (0-25 scale)
    if performance.question_1_total > 0:
        weighted_scores["question_1"] = (performance.question_1 / performance.question_1_total) * .01

    num_comparisons = performance.num_squad_comparisons
    # Questions two to ten are binary (0/1) and averaged similarly
    if num_comparisons > 0:
        for question in range(2, 11):
            question_key = f"question_{question}"
            # Calculate the average for the current question
            question_total = getattr(performance, question_key, 0)
            print(question_total)
            average = question_total / num_comparisons  # Prevent division by zero
            # Apply the weight to the average score
            weighted_scores[question_key] = average * weights[question_key]
    print(weighted_scores)
    # Sum all weighted scores to get the overall score
    overall_score = sum(weighted_scores.values()) * 100
    return overall_score
