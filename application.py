import os
# TODO: remove sys
import sys

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    #history = db.execute("SELECT * FROM portfolio WHERE id=:userId", userId=session["user_id"])
    history2 = db.execute("SELECT id, symbol, SUM(shares) FROM portfolio WHERE id=:userId GROUP BY symbol", userId=session["user_id"])
    stocks = []

    if history2:
        user = db.execute("SELECT * FROM users WHERE id=:userId", userId=session["user_id"])
        user_name = user[0]['username']
        user_cash = user[0]['cash']
        assets = 0
        assets += user_cash
        for transaction in history2:
            symbol = transaction['symbol']
            info = lookup(symbol)
            name = info['name']
            price = float(info['price'])
            shares = float(transaction['SUM(shares)'])
            total = shares * price
            assets+= total
            stockObject = {
                'symbol': symbol,
                'name': name,
                'shares': shares,
                'price': usd(price),
                'total': usd(total)
            }
            stocks.append(stockObject)
        return render_template("index.html", stocks=stocks, name=user_name, userNetWorth=usd(assets))
    else:
        return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # Check symbol
        if not request.form.get("symbol"):
            return apology("Must enter a stock symbol")

        # Check shares
        if not request.form.get("shares"):
            return apology("Must enter amount of shares")
        elif int(request.form.get("shares")) <= 0:
            return apology("Must enter a positive number of shares")

        # Get stock info
        symbol = request.form.get("symbol")
        stock = lookup(symbol)

        if not stock:
            return apology("Invalid stock symbol")

        user = db.execute("SELECT * FROM users WHERE id=:userId", userId=session["user_id"])
        totalBalance = float(user[0]["cash"])
        stockCost = stock["price"] * int(request.form.get("shares"))

        if stockCost > totalBalance:
            return apology("u is broke :D :D :D")
        else:
            # 'portfolio' table was created using the following command:
            # CREATE TABLE portfolio (transaction_id INTEGER PRIMARY KEY,
            #     id integer NOT NULL, symbol text NOT NULL, shares integer NOT NULL, price real NOT NULL)
            db.execute("INSERT INTO portfolio (id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price);",
                user_id=session["user_id"], symbol=stock["symbol"], shares=int(request.form.get("shares")), price=stockCost * -1)

            db.execute("UPDATE users SET cash=cash-:cost WHERE id=:userId;", cost=stockCost, userId=session["user_id"])
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure stock symbol is given
        if not request.form.get("symbol"):
            return apology("Must enter stock symbol")

        symbol = request.form.get("symbol")
        quote = lookup(symbol)

        if quote:
            return render_template("quoted.html", company=quote["name"], symbol=quote["symbol"], price=usd(quote["price"]))
        else:
            return apology("Must enter valid stock symbol")

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Check if username is already in the database
        if len(rows) != 0:
            return apology("username already exists", 403)

        # Ensure that password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure that password was entered twice
        if not request.form.get("confirmation"):
            return apology("enter password again to make sure they match", 403)

        # Ensure that passwords match
        if not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords must match", 403)

        # Insert data into database
        signup = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash_password)",
                            username = request.form.get("username"),
                            hash_password = generate_password_hash(request.form.get("password")))

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    #return apology("TODO")

    if request.method == "GET":
        all_symbols = []
        fake = ["A", "G", "SS"]
        history = db.execute("SELECT symbol FROM portfolio WHERE id=:userId GROUP BY symbol", userId=session["user_id"])
        for sym in history:
            all_symbols.append(sym['symbol'])
        return render_template("sell.html", stocks=all_symbols)

    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must select symbol")

        requested_shares = float(request.form.get("shares"))
        if not requested_shares:
            return apology("must choose number of shares")

        history = db.execute("SELECT id, symbol, SUM(shares) FROM portfolio WHERE id=:userId GROUP BY symbol", userId=session["user_id"])
        total_shares = 0
        shares_match = False
        for transaction in history:
            if symbol == transaction['symbol']:
                total_shares = int(transaction['SUM(shares)'])
                shares_match = True

        if shares_match and not requested_shares > total_shares :
            stock = lookup(symbol)
            total_cost = stock['price'] * requested_shares
            db.execute("INSERT INTO portfolio (id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :earnings);",
                user_id=session["user_id"], symbol=stock["symbol"], shares=int(requested_shares) * -1, earnings=total_cost)

            db.execute("UPDATE users SET cash=cash+:earnings WHERE id=:userId;", earnings=total_cost, userId=session["user_id"])
            return redirect("/")
        else:
            return apology("stock not in portfolio or too many shares requested")

    return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
