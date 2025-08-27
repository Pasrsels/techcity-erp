from django.utils import timezone
import json, datetime, openpyxl
from os import system 
import csv, base64
from django.core.files.base import ContentFile
from django.http import HttpResponse
from datetime import timedelta
from openpyxl.styles import Alignment, Font, PatternFill
from . models import *
import apps.inventory.tasks as tasks
from decimal import Decimal
from django.views import View
from django.db.models import Q, Sum, F, FloatField, ExpressionWrapper, Count
from django.db import transaction
from django.contrib import messages
from utils.utils import generate_pdf
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from apps.finance.models import (
    StockTransaction,
    PurchaseOrderAccount, 
    PurchasesAccount,
    Expense,
    Currency,
    VATTransaction, 
    VATRate,
    Account,
    Cashbook,
    ExpenseCategory,
    AccountBalance,
    AccountTransaction
)
from . utils import (
    calculate_inventory_totals, 
    average_inventory_cost,
    generete_delivery_note
)
from . forms import (
    BatchForm,
    AddProductForm, 
    addCategoryForm, 
    addTransferForm, 
    DefectiveForm,
    RestockForm, 
    AddDefectiveForm, 
    ServiceForm, 
    AddSupplierForm,
    CreateOrderForm,
    noteStatusForm,
    PurchaseOrderStatusForm,
    ReorderSettingsForm,
    EditSupplierForm,
    StockTakeForm,
    AddShrinkageForm,
    AddWriteOffForm
)
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from channels.generic.websocket import  AsyncJsonWebsocketConsumer
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from permissions.permissions import (
    admin_required,
    # sales_required, 
    # accountant_required
)
from utils.account_name_identifier import account_identifier
from loguru import logger
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.core.files.uploadedfile import InMemoryUploadedFile
from apps.inventory.utils import best_price
from collections import defaultdict
from django.core.cache import cache
from django.core.paginator import Paginator
from typing import List, Dict, Any
from apps.finance.models import UserAccount
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
