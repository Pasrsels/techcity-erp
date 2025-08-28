from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sum_expense_amount(expenses):
    """
    Custom template filter that sums the amount for a list of expenses
    """
    return sum([expense.amount for expense in expenses])

@register.filter
def abs(value):
    """
    Return the absolute value
    """
    return abs(value)