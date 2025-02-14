from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.sql.sqltypes import NULLTYPE

from .models import Note, Info, Stratification, User, Feedback, Supervisor_Notes
from . import db
import json
import random

views = Blueprint('views', __name__)


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
        Stratification.overall_elo,
        Stratification.duty_perform_elo,
        Stratification.professionalism_elo,
        Stratification.leadership_elo,
        Stratification.character_elo,
        Note.data.label("note_data"),
        Supervisor_Notes.data.label("supervisor_data")
    ).join(Info, User.id == Info.user_id) \
        .join(Stratification, User.id == Stratification.user_id, isouter=True) \
        .join(Note, User.id == Note.user_id, isouter=True) \
        .join(Supervisor_Notes, User.id == Supervisor_Notes.user_id, isouter=True) \
        .filter(Info.squadron == admin_info.squadron)

    print(class_year)
    if class_year:
        query = query.filter(Info.class_year == class_year)

    users = query.order_by(Stratification.overall_elo.desc().nullslast(), User.last_name, User.first_name).all()

    return render_template("admin_dashboard.html", users=users, squadron=admin_info.squadron, class_year=class_year)


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

    # Query for users in the same squadron and class year
    users = db.session.query(User, Note, Stratification).join(Info, Info.user_id == User.id) \
        .join(Note, Note.user_id == User.id) \
        .join(Stratification, Stratification.user_id == User.id, isouter=True) \
        .filter(Info.squadron == admin_info.squadron) \
        .filter(Info.class_year == class_year).all()

    if not users:
        flash(f"No users found for class year {class_year} in squadron {admin_info.squadron}.", category='error')
        return redirect(url_for('views.strat_users'))

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

        criteria_list = ['overall', 'duty_performance', 'professionalism', 'leadership', 'character']

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