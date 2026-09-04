from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Expense
from sqlalchemy import func
from datetime import datetime

# Create Blueprint
# "expenses" = name of this blueprint
# __name__   = current file
expenses_bp = Blueprint("expenses", __name__)


#Get all expenses
@expenses_bp.route("/", methods=["GET"])
@login_required
def get_expenses():
    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Expense.created_at.desc()
    ).all()
    return jsonify([e.to_dict() for e in expenses])

# Create expense
@expenses_bp.route("/", methods=["POST"])
@login_required
def create_expense():
    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify({"error": "No data received"}), 400

    # Check if data is a LIST (multiple) or DICT (single)
    if isinstance(data, list):
        # ── MULTIPLE EXPENSES ──
        saved = []
        errors = []

        for item in data:
            try:
                expense = Expense(
                    shop_name    = item.get("shop_name"),
                    date         = item.get("date"),
                    total_amount = item.get("total_amount"),
                    currency     = item.get("currency", "JPY"),
                    category     = item.get("category"),
                    notes        = item.get("notes"),
                    user_id      = current_user.id
                )
                db.session.add(expense)
                db.session.commit()
                saved.append(expense.to_dict())
            except Exception as e:
                db.session.rollback()
                errors.append(str(e))

        return jsonify({
            "message": f"{len(saved)} expenses saved!",
            "saved":   saved,
            "errors":  errors
        }), 201

    else:
        # ── SINGLE EXPENSE ──
        expense = Expense(
            shop_name    = data.get("shop_name"),
            date         = data.get("date"),
            total_amount = data.get("total_amount"),
            currency     = data.get("currency", "JPY"),
            category     = data.get("category"),
            notes        = data.get("notes"),
            user_id      = current_user.id
        )

        try:
            db.session.add(expense)
            db.session.commit()
            return jsonify({
                "message": "Expense saved!",
                "expense": expense.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
    
#Get Single expense by ID
@expenses_bp.route("/<int:expense_id>", methods=["GET"])
@login_required
def get_expense(expense_id):
    #Find expense by ID (scoped to current user)
    #If not found -> automatically return 404
    expense = Expense.query.filter_by(
        id=expense_id, user_id=current_user.id
    ).first_or_404()
    return jsonify(expense.to_dict())

# UPDATE 
@expenses_bp.route("/<int:expense_id>",methods=["PUT"])
@login_required
def update_expense(expense_id):
    # Step 1: Find expense (scoped to current user)
    expense = Expense.query.filter_by(
        id=expense_id, user_id=current_user.id
    ).first_or_404()
    
    # Step 2: Get new data from user
    data = request.get_json(force=True)
    
    if not data:
        return jsonify({"error":"No data received"}),400
    
    # Step 3: Update only fields that were sent
    if "shop_name"    in data: expense.shop_name    = data["shop_name"]
    if "date"         in data: expense.date         = data["date"]
    if "total_amount" in data: expense.total_amount = data["total_amount"]
    if "currency"     in data: expense.currency     = data["currency"]
    if "category"     in data: expense.category     = data["category"]
    if "notes"        in data: expense.notes        = data["notes"]
    
    # Step 4: Save changes
    try:
        db.session.commit()
        return jsonify({
            "message": "Expense updated!",
            "expense":expense.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}),500
    
# DELETE EXPENSE
@expenses_bp.route("/<int:expense_id>",methods=["DELETE"])
@login_required
def delete_expense(expense_id):
    # Step 1 : Find Expense (scoped to current user)
    expense = Expense.query.filter_by(
        id=expense_id, user_id=current_user.id
    ).first_or_404()
    
    #Step 2 :Delete it
    try:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({
            "message":f"Expense{expense_id} deleted!"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}),500
    
# DASHBOARD STATS
@expenses_bp.route("/stats", methods=["GET"])
@login_required
def getstats():
    # Get current month and year
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # TOTAL THIS MONTH
    total_month = db.session.query(
        func.sum(Expense.total_amount)
    ).filter(
        Expense.user_id == current_user.id,
        func.strftime("%m",Expense.date) == f"{current_month:02d}",
        func.strftime("%Y",Expense.date) == str(current_year)
    ).scalar() or 0

    # Total this year
    total_year = db.session.query(
        func.sum(Expense.total_amount)
    ).filter(
        Expense.user_id == current_user.id,
        func.strftime("%Y", Expense.date) == str(current_year)
    ).scalar() or 0

    # Count this month
    count_month = db.session.query(
        func.count(Expense.id)
    ).filter(
        Expense.user_id == current_user.id,
        func.strftime("%m",Expense.date) == f"{current_month:02d}",
        func.strftime("%Y",Expense.date) == str(current_year)
    ).scalar() or 0

    # TOP CATEGORY THIS MONTH
    top_category = db.session.query(
        Expense.category,
        func.sum(Expense.total_amount).label("total")
    ).filter(
        Expense.user_id == current_user.id,
        func.strftime("%m",Expense.date) == f"{current_month:02d}",
        func.strftime("%Y",Expense.date) == str(current_year),
        Expense.category != None
    ).group_by(
        Expense.category
    ).order_by(
        func.sum(Expense.total_amount).desc()
    ).first()

    #Monthly breakdown( last 6 months )
    monthly = db.session.query(
        func.strftime("%Y-%m", Expense.date).label("month"),
        func.sum(Expense.total_amount).label("total")
    ).filter(
        Expense.user_id == current_user.id
    ).group_by(
        func.strftime("%Y-%m", Expense.date)
    ).order_by(
        func.strftime("%Y-%m", Expense.date).desc()
    ).limit(6).all()

    # ── Category breakdown ──
    categories = db.session.query(
        Expense.category,
        func.sum(Expense.total_amount).label("total"),
        func.count(Expense.id).label("count")
    ).filter(
        Expense.user_id == current_user.id,
        Expense.category != None
    ).group_by(
        Expense.category
    ).order_by(
        func.sum(Expense.total_amount).desc()
    ).all()

    # ── Average per day this month ──
    avg_per_day = db.session.query(
        func.avg(Expense.total_amount)
    ).filter(
        Expense.user_id == current_user.id,
        func.strftime("%m", Expense.date) == f"{current_month:02d}",
        func.strftime("%Y", Expense.date) == str(current_year)
    ).scalar() or 0

    return jsonify({
        "total_this_month":   round(total_month, 2),
        "total_this_year":    round(total_year, 2),
        "expense_count":      count_month,
        "top_category":       top_category[0] if top_category else None,
        "average_per_day":    round(avg_per_day, 2),
        "monthly_chart": [
            {
                "month": row.month,
                "total": round(row.total, 2)
            }
            for row in reversed(monthly)
        ],
        "category_breakdown": [
            {
                "category": row.category or "Uncategorized",
                "total":    round(row.total, 2),
                "count":    row.count
            }
            for row in categories
        ]
    })