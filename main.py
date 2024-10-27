import os
import tempfile
import csv
from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import random
import base64

app = Flask(__name__)

# Function to connect to SQLite database
def get_db_connection():
    conn = sqlite3.connect('D:/Proton Drive/My files/לימודים/סמינר כרמית/אתר חדש/reddit_analysis.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to get one random post for analysis
def get_random_post():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve one random post that is not tagged as irrelevant or non-meme
    query = '''
    SELECT * FROM posts 
    WHERE id NOT IN (
        SELECT PostId FROM Tags WHERE Name IN ('irrelevant', 'non-meme')
    )
    ORDER BY RANDOM() 
    LIMIT 1
    '''
    
    post = cursor.execute(query).fetchone()
    
    # Fetch associated media for that post
    if post:
        media = cursor.execute('SELECT * FROM media WHERE post_id = ?', (post['id'],)).fetchone()
        if media:
            media = dict(media)  # Convert Row object to dictionary
            media['data'] = base64.b64encode(media['data']).decode('utf-8')  # Base64 encode media data
    else:
        media = None

    conn.close()
    return post, media

# Route to display one post at a time and show analyzed counts
@app.route('/')
def show_post():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count the number of analyzed posts per month
    analyzed_counts = cursor.execute('''
        SELECT strftime('%Y-%m', p.date) as month, COUNT(a.post_id) as analyzed_count
        FROM posts p 
        JOIN analysis a ON p.id = a.post_id
        GROUP BY month
    ''').fetchall()

    # Try to find a post from a month that doesn't have 10 posts analyzed yet and has not been analyzed
    post = cursor.execute('''
        SELECT * FROM posts 
        WHERE id NOT IN (
            SELECT PostId FROM Tags WHERE Name IN ('irrelevant', 'non-meme')
        )
        AND id NOT IN (SELECT post_id FROM analysis)  -- Exclude already analyzed posts
        AND strftime('%Y-%m', date) IN (
            SELECT strftime('%Y-%m', date) as month
            FROM posts
            LEFT JOIN analysis a ON posts.id = a.post_id
            GROUP BY month
            HAVING COUNT(a.post_id) < 10
        )
        ORDER BY RANDOM() 
        LIMIT 1
    ''').fetchone()

    # Fetch associated media for that post
    if post:
        media = cursor.execute('SELECT * FROM media WHERE post_id = ?', (post['id'],)).fetchone()
        if media:
            media = dict(media)
            media['data'] = base64.b64encode(media['data']).decode('utf-8')
        current_month = cursor.execute('''
            SELECT COUNT(a.post_id) as analyzed_count
            FROM posts p
            JOIN analysis a ON p.id = a.post_id
            WHERE strftime('%Y-%m', p.date) = strftime('%Y-%m', ?)
        ''', (post['date'],)).fetchone()
        analyzed_count = current_month['analyzed_count'] if current_month else 0
    else:
        media = None
        analyzed_count = 0




    conn.close()
    return render_template('post.html', post=post, media=media, analyzed_counts=analyzed_counts, analyzed_count=analyzed_count)

@app.route('/get_post_details/<int:post_id>', methods=['GET'])
def get_post_details(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the post details using post_id
    cursor.execute('''
        SELECT p.title, p.content, a.content AS analysis_content, a.form AS form_analysis, a.stance AS stance_analysis, m.data AS media_data
        FROM posts p
        JOIN analysis a ON p.id = a.post_id
        LEFT JOIN media m ON p.id = m.post_id
        WHERE p.id = ?
    ''', (post_id,))

    post = cursor.fetchone()

    conn.close()

    # If the post doesn't exist, return 404
    if not post:
        return {"error": "Post not found"}, 404
    media_data = ''
    # Convert the media_data BLOB to base64 if available
    if post['media_data']:
        media_data = base64.b64encode(post['media_data']).decode('utf-8')

    return {
        "title": post['title'],
        "content": post['content'],
        "analysis_content": post['analysis_content'],
        "form_analysis": post['form_analysis'],
        "stance_analysis": post['stance_analysis'],
        "media_data": media_data
    }

# Route to load a specific post by ID
@app.route('/post/<int:post_id>')
def load_post_by_id(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the post with the given post_id
    post = cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()

    # Fetch associated media for that post
    media = cursor.execute('SELECT * FROM media WHERE post_id = ?', (post_id,)).fetchone()
    if media:
        media = dict(media)
        media['data'] = base64.b64encode(media['data']).decode('utf-8')

    # Check if this post has already been analyzed
    analysis = cursor.execute('SELECT * FROM analysis WHERE post_id = ?', (post_id,)).fetchone()

    conn.close()

    # Pass the analysis data to the template if it exists
    if post:
        return render_template('post.html', post=post, media=media, analysis=analysis)
    else:
        return f"Post with ID {post_id} not found", 404
@app.route('/post', methods=['GET'])
def redirect_to_post():
    post_id = request.args.get('post_id')  # Get post_id from form
    return redirect(url_for('load_post_by_id', post_id=post_id))  # Pass post_id to the URL builder


# Function to get analyzed posts and export them to a CSV
@app.route('/export')
def export_analysis():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get analyzed posts and their analysis
    analyzed_posts = cursor.execute('''
        SELECT p.id, p.title, p.content, p.date, a.content AS content_analysis, 
                  a.form AS form_analysis, a.stance AS stance_analysis 
        FROM posts p 
        JOIN analysis a ON p.id = a.post_id
    ''').fetchall()
    
    conn.close()
    
    # Use a temporary directory for writing the CSV file
    temp_dir = tempfile.gettempdir()
    csv_file_path = os.path.join(temp_dir, 'analyzed_posts.csv')
    
    # Create CSV file for download
    with open(csv_file_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['Post ID', 'Title', 'Content', 'Date', 'Content Analysis', 'Form Analysis', 'Stance Analysis', 'Post Link'])
        
        for post in analyzed_posts:
            # Create an internal link to the post's page
            post_link = url_for('load_post_by_id', post_id=post['id'], _external=True)
            writer.writerow([post['id'], post['title'], post['content'], post['date'], post['content_analysis'], post['form_analysis'], post['stance_analysis'], post_link])
    
    # Send the CSV file to the user
    return send_file(csv_file_path, as_attachment=True)

@app.route('/analyzed')
def view_analyzed():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure the correct column name is used (in this case, it should be post_id, not PostId)
    analyzed_posts = cursor.execute(
        "SELECT * FROM posts WHERE id IN (SELECT post_id FROM analysis)"
    ).fetchall()

    # Get a list of all months that have posts (whether analyzed or not)
    months_with_posts = cursor.execute('''
        SELECT DISTINCT strftime('%Y-%m', date) AS month
        FROM posts
        ORDER BY month
    ''').fetchall()

    # Count how many posts from each month have been analyzed
    analyzed_counts = cursor.execute('''
        SELECT strftime('%Y-%m', p.date) AS month, COUNT(a.post_id) AS count
        FROM posts p
        LEFT JOIN analysis a ON p.id = a.post_id
        GROUP BY month
        ORDER BY month
    ''').fetchall()

    conn.close()
    
    return render_template('analyzed.html', analyzed_posts=analyzed_posts, months_with_posts=months_with_posts, analyzed_counts=analyzed_counts)

@app.route('/analyze_by_month', methods=['GET'])
def analyze_by_month():
    month = request.args.get('month')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Select a random post from the chosen month that has not yet been analyzed
    post = cursor.execute('''
        SELECT * FROM posts
        WHERE id NOT IN (SELECT post_id FROM analysis)
        AND strftime('%Y-%m', date) = ?
        ORDER BY RANDOM()
        LIMIT 1
    ''', (month,)).fetchone()

    # Fetch associated media for that post
    media = cursor.execute('SELECT * FROM media WHERE post_id = ?', (post['id'],)).fetchone()
    if media:
        media = dict(media)
        media['data'] = base64.b64encode(media['data']).decode('utf-8')

    # Count how many posts have been analyzed in this month
    analyzed_count = cursor.execute('''
        SELECT COUNT(*) AS count
        FROM posts p
        JOIN analysis a ON p.id = a.post_id
        WHERE strftime('%Y-%m', p.date) = ?
    ''', (month,)).fetchone()['count']

    conn.close()

    return render_template('post.html', post=post, media=media, analyzed_count=analyzed_count)

# Route to display rejected posts
@app.route('/rejected')
def view_rejected():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Make sure the Tags table has a column named PostId (correct capitalization)
    rejected_posts = cursor.execute(
        "SELECT * FROM posts WHERE id IN (SELECT PostId FROM Tags WHERE Name = 'irrelevant')"
    ).fetchall()
    conn.close()
    return render_template('rejected.html', posts=rejected_posts)

# Route for analyzing a post or rejecting it
@app.route('/analyze', methods=['POST'])
def analyze_post():
    post_id = request.form['post_id']
    action = request.form['action']

    conn = get_db_connection()
    cursor = conn.cursor()

    if action == 'reject':
        # Mark post as rejected
        cursor.execute("INSERT INTO Tags (PostId, Name) VALUES (?, 'irrelevant')", (post_id,))
    elif action == 'analyze':
        # Check if an analysis already exists for this post
        existing_analysis = cursor.execute("SELECT * FROM analysis WHERE post_id = ?", (post_id,)).fetchone()

        content_analysis = request.form['content']
        form_analysis = request.form['form']
        stance_analysis = request.form['stance']

        if existing_analysis:
            # Update the existing analysis
            cursor.execute(
                "UPDATE analysis SET content = ?, form = ?, stance = ? WHERE post_id = ?",
                (content_analysis, form_analysis, stance_analysis, post_id)
            )
        else:
            # Insert a new analysis if one doesn't exist
            cursor.execute(
                "INSERT INTO analysis (post_id, content, form, stance) VALUES (?, ?, ?, ?)",
                (post_id, content_analysis, form_analysis, stance_analysis)
            )

    conn.commit()
    conn.close()
    
    return redirect(url_for('show_post'))

@app.route('/kanban')
def kanban_board():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch only posts that have been analyzed (i.e., exist in the analysis table)
    posts = cursor.execute('''
        SELECT p.id, p.title, p.content, p.date, a.content AS analysis_content, a.form AS form_analysis, a.stance AS stance_analysis, m.data AS media_data, p.post_group
        FROM posts p
        JOIN analysis a ON p.id = a.post_id
        LEFT JOIN media m ON p.id = m.post_id
        ORDER BY p.date DESC
    ''').fetchall()

    # Convert BLOB data to base64 for image rendering
    posts_with_images = []
    for post in posts:
        post = dict(post)
        if post['media_data']:
            post['media_data'] = base64.b64encode(post['media_data']).decode('utf-8')
        posts_with_images.append(post)

    # Fetch distinct groups (kanban columns) for the posts
    groups = cursor.execute('''
        SELECT DISTINCT post_group
        FROM posts
        WHERE id IN (SELECT post_id FROM analysis)
    ''').fetchall()

    conn.close()

    return render_template('kanban.html', groups=groups, posts=posts_with_images)
@app.route('/update_post_group/<int:post_id>/<new_group>', methods=['POST'])
def update_post_group(post_id, new_group):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update the post's group in the database
    cursor.execute('UPDATE posts SET post_group = ? WHERE id = ?', (new_group, post_id))
    conn.commit()
    conn.close()

    return '', 204  # Return no content to indicate success


# Helper function to generate random color
def get_random_color():
    return "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])

import base64

@app.route('/analyzed_list', methods=['GET'])
def analyzed_list():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all analyzed posts
    cursor.execute('''
        SELECT p.id, p.title, p.post_group, a.content AS analysis_content, a.form AS form_analysis, a.stance AS stance_analysis, m.data AS media_data
        FROM posts p
        JOIN analysis a ON p.id = a.post_id
        LEFT JOIN media m ON p.id = m.post_id
        ORDER BY p.post_group, p.id
    ''')

    # Convert fetched posts into a list of dictionaries
    posts = [dict(post) for post in cursor.fetchall()]

    # Base64 encode the image data (if media_data exists)
    for post in posts:
        if post['media_data']:
            post['media_data'] = base64.b64encode(post['media_data']).decode('utf-8')

    # Fetch all unique groups for filtering options
    cursor.execute('SELECT DISTINCT post_group FROM posts WHERE post_group IS NOT NULL')
    groups = [dict(group) for group in cursor.fetchall()]
    group_colors = {group['post_group']: get_random_color() for group in groups}

    conn.close()

    return render_template('analyzed_list.html', posts=posts, group_colors=group_colors, groups=groups)

if __name__ == '__main__':
    app.run(debug=True)
