from django.contrib.auth import authenticate
from loguru import logger
from ..tasks import send_expense_creation_notification
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from django.http import FileResponse
import io
from collections import defaultdict
from apps.pos.utils.receipt_signature import generate_receipt_data
from apps.pos.utils.submit_receipt_data import submit_receipt_data
from django.db.models.functions import Coalesce
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.utils.dateparse import parse_date
from dotenv import load_dotenv
from apps.settings.models import OfflineReceipt, FiscalDay, FiscalCounter
from utils.zimra import ZIMRA
from utils.zimra_sig_hash import run
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, F, Value, CharField, ExpressionWrapper
import datetime
from itertools import chain
from django.core.paginator import Paginator, EmptyPage
import imghdr, base64
from django.core.files.base import ContentFile
from ..models import *
from ..serializers import ExpenseSerializer
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
