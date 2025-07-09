from flask import Flask, jsonify, request, render_template, url_for, redirect
from flask import request, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client.blog_database

# Визначення колекцій
articles = db['articles']
categories = db['categories']
comments = db['comments']
users = db['users']

@app.route('/add-article')
def add_article_form():
    return render_template('add_article.html')

@app.route('/add-category')
def add_category_form():
    return render_template('add_category.html', caption='Додати категорію')

@app.route('/')
def home():
    # endpoints = {
    #     "Welcome": "/",
    #     "Create Article": "/add-article",
    #     "Get All Articles": "/articles",
    #     "Create Post": "/posts [POST]",
    #     "Get All Posts": "/posts [GET]"
    # }
    # return jsonify(endpoints)

    menu = [
        {
            "menuname": "Статті",
            "submenu": [
                {"sub": "Створити статтю", "path": "/add-article"},
                {"sub": "Переглянути усі статті", "path": "/articles"}
            ]
        },
        {
            "menuname": "Категорії",
            "submenu": [
                {"sub": "Створити категорію", "path": "/add-category"},
                {"sub": "Переглянути усі категорії", "path": "/categories"}
            ]
        }
    ]

    return render_template('index.html', menu=menu)


@app.route('/articles', methods=['POST'])
def create_article():
    if request.is_json:
        # Handling JSON payload
        article_data = request.get_json()
    else:
        # Handling form data
        article_data = request.form

    article = {
        "title": article_data.get("title"),
        "content": article_data.get("content"),
        "publishedDate": article_data.get("publishedDate", None),
        "category": article_data.get("category", None),
        "author": article_data.get("author", None)
    }
    articles.insert_one(article)
    return redirect(url_for('get_articles'))

@app.route('/categories', methods=['POST'])
def create_category():
    if request.is_json:
        # Handling JSON payload
        category_data = request.get_json()
    else:
        # Handling form data
        category_data = request.form

    category = {
        "title": category_data.get("title"),

    }
    categories.insert_one(category)
    # return jsonify({"message": "category created successfully"}), 201
    return redirect(url_for('get_categories'))

@app.route('/categories', methods=['GET'])
def get_categories():
    all_categories = list(categories.find())
    return render_template('all_categories.html', caption='Список усіх категорій', all_categories=all_categories)

@app.route('/articles', methods=['GET'])
def get_articles():
    all_articles = list(articles.find())
    for article in all_articles:
        article['_id'] = str(article['_id'])  # Convert ObjectId to string for HTML rendering
    return render_template('all_articles.html', all_articles=all_articles)

@app.route('/posts', methods=['POST'])
def create_post():
    post = {
        "title": request.json['title'],
        "author": request.json['author'],
        "content": request.json['content'],
        "tags": request.json.get('tags', []),
        "date": request.json.get('date')
    }
    db.posts.insert_one(post)
    return jsonify({'message': 'Post created successfully!'}), 201

@app.route('/posts', methods=['GET'])
def get_posts():
    posts = db.posts.find()
    result = []
    for post in posts:
        post['_id'] = str(post['_id'])  
        result.append(post)
    return jsonify(result)

@app.route('/articles/<article_id>/comments', methods=['POST'])
def add_comment(article_id):
    try:
        comment_data = request.get_json()
        comment = {
            "article_id": ObjectId(article_id),  # Ensure the article ID is an ObjectId
            "content": comment_data['content'],
            "author": comment_data['author'],
            "created_at": datetime.utcnow()  # Capture the current time as the creation time
        }
        comments.insert_one(comment)
        return jsonify({"message": "Comment added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/articles/<article_id>/comments', methods=['GET'])
def get_comments(article_id):
    try:
        article_comments = comments.find({"article_id": ObjectId(article_id)})
        comments_list = [{
            "content": comment['content'],
            "author": comment['author'],
            "created_at": comment['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        } for comment in article_comments]
        return jsonify(comments_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    

@app.route('/add-comment', methods=['GET'])
def add_comment_form():
    all_articles = list(articles.find({}, {'title': 1}))  
    for article in all_articles:
        article['_id'] = str(article['_id'])  
    return render_template('add_comment.html', all_articles=all_articles)


@app.route('/submit-comment', methods=['POST'])
def submit_comment():
    try:
        article_id = request.form['article_id']
        author = request.form['author']
        content = request.form['content']
        
        # Create the comment document
        comment = {
            "article_id": ObjectId(article_id),
            "author": author,
            "content": content,
            "created_at": datetime.utcnow()
        }
        comments.insert_one(comment)  # Insert the comment

        # Redirect to the route that shows all comments
        return redirect(url_for('all_comments'))
    except Exception as e:
        print(e)  # Print the error for debugging
        return redirect(url_for('add_comment_form'))  # Redirect back to the comment form in case of an error
    
@app.route('/all-comments')
def all_comments():
    try:
        # Fetch all comments from the database
        all_comments = list(comments.find({}))
        for comment in all_comments:
            comment['created_at'] = comment['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            # Fetch the article title for each comment
            article = articles.find_one({"_id": comment['article_id']})
            comment['article_title'] = article['title'] if article else "Unknown Article"
        return render_template('all_comments.html', comments=all_comments)
    except Exception as e:
        print(e)
        return "An error occurred", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create user document
        user = {
            "name": name,
            "email": email,
            "password": hashed_password
        }

        try:
            # Insert user into the database
            db.users.insert_one(user)
            flash('User registered successfully!')
            return redirect(url_for('login'))  # Redirect to the login page or wherever appropriate
        except DuplicateKeyError:
            flash('Email already registered.')
            return render_template('register.html'), 409

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
