from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort, make_response
from flask_pymongo import PyMongo
import flask
from bson.json_util import dumps
from flask import Response
from bson import json_util

app = flask.Flask(__name__)

app.config["MONGO_URI"] = "mongodb+srv://engaezik:ozOlNDhqiyCzT0XL@cluster0.goiqv0u.mongodb.net/shop?retryWrites=true&w=majority"

mongodb_client = PyMongo(app)
db = mongodb_client.db

@app.route('/')
def index():
    return render_template('index.html', a='b')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/add_one')
def add_one():
    db.todos.insert_one({'title': "todo title", 'body': "todo body"})
    return flask.jsonify(message="success")

@app.route('/get_users')
def get_users():
    users = db.users.find()
    return Response(dumps([user for user in users]),
                    mimetype='application/json')

@app.route('/create_user', methods = ['POST'])
def create_user():
    if request.cookies.get('is_admin') != "True":
        abort(403, "You have no access rights")

    username = request.json["username"]
    size = db.users.find_one({"username": username})
    if size:
        abort(409, jsonify(message='User is already exists'))
    else:
        db.users.insert_one({'username': username,
                             'average_rating': -1.0,
                             'all_rates': 0,
                             'reviews': [],
                             'is_admin': False,
                             'password': ''
                             })
    return jsonify(message="success")

@app.route('/create_item', methods = ['POST'])
def create_item():
    if request.cookies.get('is_admin') != "True":
        abort(403, "You have no access rights")

    items = request.json
    size = db.items.find_one({"name": items["name"]})
    if size:
        abort(409, jsonify(message='Item is already exists'))
    else:
        items["reviews"] = []
        items["rate"] = 0.0
        items["all_rates"] = 0
        db.items.insert_one(items)
    return jsonify(message="success")

@app.route('/authorize')
def authorize():
    username = request.args['username']
    password = request.args['password']
    redirect_uri = request.args.get('redirect', '/')

    name = db.users.find_one({"username": username, "password": password})

    if name:
        res = make_response(jsonify({"status": "success", "redirect_url": authorized()}))
        res.set_cookie('username', username, max_age=60 * 60)
        is_admin = name["is_admin"]
        res.set_cookie('is_admin', str(is_admin), max_age=60 * 60)
        return res
    else:
        return jsonify({"status": "failure", "message": "User does not exist"}), 401
@app.route('/authorized')
def authorized():
    return render_template('authorized.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/delete_user', methods = ['DELETE'])
def delete_user():
    if request.cookies.get('is_admin') != "True":
        abort(403, "You have no access rights")

    username = request.json["username"]
    size = db.users.find_one({"username": username})
    if size:
        db.users.delete_one({"username": username})
    else:
        abort(404, jsonify(message='User does not exists'))

    return jsonify(message="success")

@app.route('/delete_item', methods = ['DELETE'])
def delete_item():
    if request.cookies.get('is_admin') != "True":
        abort(403, "You have no access rights")

    name = request.json["name"]
    size = db.items.find_one({"name": name})
    if size:
        db.items.delete_one({"name": name})
    else:
        abort(404, jsonify(message='Item does not exists'))

    return jsonify(message="success")

@app.route('/rate_item', methods = ['POST'])
def rate_item():
    if not request.cookies.get('username'):
        abort(403, "You have no access rights")

    name_items = request.json["name"]
    rate_items = request.json["rate"]

    item = db.items.find_one({"name": name_items})
    if not item:
        abort(404, 'Item does not exists')
    else:
        sum_rate = item["rate"] * item["all_rates"]
        sum_rate += rate_items
        item["all_rates"] += 1
        item["rate"] = sum_rate / item["all_rates"]

        db.items.replace_one({"name": name_items}, item)

    user = db.users.find_one({"username": request.cookies.get('username')})
    if not user:
        abort(404, 'User does not exists')
    else:
        print(user["average_rating"], type(user["average_rating"]), user["all_rates"], type(user["all_rates"]))
        sum_rate = user["average_rating"] * user["all_rates"]
        sum_rate += rate_items
        user["all_rates"] += 1
        user["average_rating"] = sum_rate / user["all_rates"]

        db.users.replace_one({"username": request.cookies.get('username')}, user)
    return jsonify(message="success")

@app.route('/review_item', methods = ['POST'])
def review_item():
    if not request.cookies.get('username'):
        abort(403, "You have no access rights")

    name_items = request.json["name"]
    review = request.json["review"]

    item = db.items.find_one({"name": name_items})
    user = db.users.find_one({"username": request.cookies.get('username')})
    if not item:
        abort(404, 'Item does not exist')
    elif not user:
        abort(404, 'User does not exists')
    else:
        review_dict = {
            "user": user["_id"],
            "item": item["_id"],
            "value": review,
        }
        db.items.update_one({"name": name_items}, {"$push": {"reviews": review_dict}})
        db.users.update_one({"username": request.cookies.get('username')}, {"$push": {"reviews": review_dict}})

    return jsonify(message="success")


if __name__ == "__main__" :
    app.run(debug=True)
