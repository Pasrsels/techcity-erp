import  json
from rest_framework import views, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from ..serializers import *
from rest_framework.viewsets import ModelViewSet
from .serializers import *
from django.db import transaction
from django.db.models import Q, Sum, F, FloatField, ExpressionWrapper
from django.core.files.base import ContentFile
import base64
from decimal import Decimal
from ..forms import *
from ..views import get_stock_account_data
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from openpyxl.styles import Alignment, Font, PatternFill
from django.http.response import JsonResponse
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend


class AddInventoryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InventorySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            inventory = serializer.save()
            return Response({
                'status': 'success',
                'message': 'Product added successfully!',
                'product': {
                    'id': inventory.id,
                    'name': inventory.name
                }
            })
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class InventoryViewset(viewsets.ModelViewSet):
    serializer_class = InventorySerializer

    def get_queryset(self):
        user = self.request.user
        inventory_details = Inventory.objects.filter(disable=False).values()
        return Response(inventory_details, status.HTTP_200_OK)

class CategoriesList(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request): 
        categories = ProductCategory.objects.all().values()
        logger.info(categories)
        return Response(categories, status.HTTP_200_OK)

class AddCategories(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        data = request.data
        category_name = data.get('name').upper()
        
        if ProductCategory.objects.filter(name=category_name).exists():
            return Response({'message':'Category Exists'}, status.HTTP_400_BAD_REQUEST)
        
        category = ProductCategory.objects.create(
            name=category_name
        )
        return Response({'id': category.id, 'name':category.name},status.HTTP_201_CREATED)        

class ProductsListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'category__name']
    ordering_fields = ['name', 'price', 'quantity']
    ordering = ['name']
    filterset_fields = ['category__name', 'price']
    
    def get_queryset(self):
        return Inventory.objects.filter(
            branch=self.request.user.branch,
            status=True,
            disable=False
        ).select_related('category', 'branch').values(
            'id',
            'name',
            'quantity',
            'price',
            'dealer_price',
            'category__name',
            'image'
        )

class AddProducts(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # payload
        """
            id,
            name,
            cost: float,
            quantity: int,
            category,
            tax_type,
            min_stock_level,
            description
        """
        try:
            data = request.data
            product_id = data.get('id', '')
            logger.info(product_id)   
        except Exception as e:
            return Response({'message':'Invalid data'}, status.HTTP_400_BAD_REQUEST)

        image_data = data.get('image')
        if image_data:
            try:
                format, imgstr = image_data.split(';base64,') 
                ext = format.split('/')[-1]
                image = ContentFile(base64.b64decode(imgstr), name=f'{data.get('name')}.{ext}')
            except Exception as e:
                logger.error(f'Error decoding image: {e}')
                return Response({'message': 'Invalid image data'}, status.HTTP_400_BAD_REQUEST)

        try:
            category = ProductCategory.objects.get(id=data.get('category'))
        except ProductCategory.DoesNotExist:
            return Response({'message':'Category Doesnt Exists'}, status.HTTP_400_BAD_REQUEST)
        
        if product_id:
            """editing the product"""
            logger.info(f'Editing product ')
            product = Inventory.objects.get(id=product_id, branch=request.user.branch)
            product.name = data.get('name')
            product.price = data.get('price', 0)
            product.cost = data.get('cost', 0)    
            product.quantity = data.get('quantity', 0)  
            product.category = category  
            product.tax_type = data.get('tax_type')
            product.stock_level_threshold = data.get('min_stocklevel')
            product.description = data.get('description')
            product.end_of_day = True if data.get('end_of_day') else False
            product.service = True if data.get('service') else False
            product.image=product.image
            product.batch = product.batch
        else:
            """creating a new product"""
            # validation for existance
            if Inventory.objects.filter(name=data.get('name')).exists():
                return Response({'message':f'Product {data.get('name')} exists'}, status.HTTP_400_BAD_REQUEST)
            logger.info(f'Creating ')
            product = Inventory.objects.create(
                batch = '',
                name = data.get('name'),
                price = 0,
                cost = 0,
                quantity = 0,
                category = category,
                tax_type = data.get('tax_type'),
                stock_level_threshold = data.get('min_stock_level'),
                description = data.get('description'), 
                end_of_day = True if data.get('end_of_day') else False,
                service = True if data.get('service') else False,
                branch = request.user.branch,
                # image = image,
                status = True
            )
        product.save()
        return Response(status.HTTP_201_CREATED)

class DeleteProducts(views.APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request):
        try:
            data = request.data
            product_id = data.get('id', '')
            product = Inventory.objects.get(id=product_id, branch=request.user.branch)

            logger.info(product)
            if product.quantity > 0:
                product.disable = True
                return Response({'False': True, 'message': 'Product cannot be deleted it have quantity more than zero.'})
            else:
                product.disable = True
            product.save()
            return Response({'message': 'Product deleted successfully.'}, status.HTTP_200_OK)
        except Inventory.DoesNotExist:
            return Response({'message': 'Product not found.'}, status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.info(e)
            return Response({'message': str(e)}, status.HTTP_406_NOT_ACCEPTABLE)

class InventoryList(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        
        logger.info(list(Inventory.objects.\
        filter(branch=request.user.branch, status=True).values()))
        inventory_data = Inventory.objects.filter(branch=request.user.branch, status=True).values()
        logger.info(inventory_data)
        inventory = Inventory.objects.filter(branch=request.user.branch, status=True, disable=False).select_related(
        'category',
        'branch'
        ).order_by('name').values()
        return Response(
            {
                'inventory':inventory_data,
                'total_cost':inventory.aggregate(total_cost=Sum(F('quantity') * F('cost')))['total_cost'] or 0,
                'total_price':inventory.aggregate(total_price=Sum(F('quantity') * F('price')))['total_price'] or 0,
            }, 
            status.HTTP_200_OK
        )
    
class DeleteInventory(views.APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, id):
        product_id = id

        if product_id:
            inv = Inventory.objects.get(id=product_id, branch=request.user.branch)
            inv.status = False
            inv.save()
        
            ActivityLog.objects.create(
                    branch = request.user.branch,
                    user=request.user,
                    action= 'deactivated',
                    inventory=inv,
                    quantity=inv.quantity,
                    total_quantity=inv.quantity
                )
            return Response(status.HTTP_202_ACCEPTED)
        return Response(status.HTTP_406_NOT_ACCEPTABLE)
    
class EditInventory(views.APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, product_id):
        inv_product = Inventory.objects.get(id=product_id, branch=request.user.branch)
        end_of_day = request.data.get('end_of_day')

        if end_of_day:
            inv_product.end_of_day = True
        
        selling_price = Decimal(request.data.get('price'))
        dealer_price = Decimal(request.data.get('dealer_price'))
        
        # think through
        quantity = inv_product.quantity
        inv_product.name=request.data.get('name')
        # inv_product.batch=request.data['batch_code']
        inv_product.description=request.data.get('description')
        inv_product.price = Decimal(request.data.get('price'))
        inv_product.cost = Decimal(request.data.get('cost'))
        inv_product.dealer_price = Decimal(request.data.get('dealer_price'))
        inv_product.stock_level_threshold = request.data.get('min_stock_level')
        inv_product.dealer_price = dealer_price
        inv_product.quantity = request.data.get('quantity')
        inv_product.save()
        
        ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= 'Edit',
            inventory=inv_product,
            quantity=quantity,
            total_quantity=inv_product.quantity,
            dealer_price = dealer_price,
            selling_price = selling_price
        )
        return Response({'product':inv_product, 'title':f'Edit >>> {inv_product.name}'}, status.HTTP_202_ACCEPTED)

class InventoryDetail(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        purchase_order_items = PurchaseOrderItem.objects.all()
        inventory = Inventory.objects.get(id=id, branch=request.user.branch)
        logs = ActivityLog.objects.filter(
            inventory=inventory,
            branch=request.user.branch
        ).order_by('-timestamp__date', '-timestamp__time')

        # stock account data and totals (costs and quantities)
        stock_account_data = get_stock_account_data(logs)
        total_debits = sum(entry['cost'] for entry in stock_account_data if entry['type'] == 'debits')
        total_credits = sum(entry['cost'] for entry in stock_account_data if entry['type'] == 'credits')

        total_debits_quantity = sum(entry['quantity'] for entry in stock_account_data if entry['type'] == 'debits')
        total_credits_quantity = sum(entry['quantity'] for entry in stock_account_data if entry['type'] == 'credits')

        logger.info(f'debits {total_debits_quantity}')

        remaining_stock_quantity = total_debits_quantity - total_credits_quantity

        """ get inventory value based on the currencies in the system """
        inventory_value = []
        inventory_sold_value = []
        inventory_total_cost = inventory.cost * inventory.quantity

        for currency in Currency.objects.all():
            inventory_value.append(
                {
                    'name': f'{currency.name}',
                    'value': float(inventory_total_cost * currency.exchange_rate )if currency.exchange_rate == 1\
                            else float(inventory_total_cost * currency.exchange_rate)
                }
            )
            inventory_sold_value.append(
                {
                    'name': f'{currency.name}',
                    'value': logs.filter(invoice__invoice_return = False, invoice__currency=currency).\
                            aggregate(Sum('invoice__amount'))['invoice__amount__sum'] or 0
                }
            )
        
        logger.info(f'inventory value: {inventory_sold_value}')

        # logs = ActivityLog.objects.annotate(hour=Extract('timestamp', 'hour')).order_by('-hour')

        """ create log data structure for the activity log graph """
        sales_data = {}
        stock_in_data = {}
        transfer_data = {}
        labels = []

        for log in logs:
            month_name = log.timestamp.strftime('%B')  
            year = log.timestamp.strftime('%Y')
            month_year = f"{month_name} {year}"  

            if log.action == 'Sale':
                if month_year in sales_data:
                    sales_data[month_year] += log.quantity
                else:
                    sales_data[month_year] = log.quantity
            elif log.action in ('stock in', 'Update'):
                if month_year in stock_in_data:
                    stock_in_data[month_year] += log.quantity
                else:
                    stock_in_data[month_year] = log.quantity
            elif log.action == 'Transfer':
                if month_year in transfer_data:
                    transfer_data[month_year] += log.quantity
                else:
                    transfer_data[month_year] = log.quantity

            if month_year not in labels:
                labels.append(month_year)

        """ download a log or stock account pdf """

        # if request.data.get('logs'):
        #     print(request.data.get('logs'))
        #     download_stock_logs_account('logs', logs, inventory)
        # elif request.data.get('account'):
        #     download_stock_logs_account('account', logs, inventory)
        
        inventory_serializer = InventorySerializer(inventory)
        return Response({
            'inventory': inventory_serializer,
            'remaining_stock_quantity':remaining_stock_quantity,
            'stock_account_data':stock_account_data,
            'inventory_value':inventory_value,
            'inventory_sold_value':inventory_sold_value,
            'total_debits':total_debits,
            'total_credits':total_credits,
            'logs': logs,
            'items':purchase_order_items,
            'sales_data': sales_data.values(), 
            'stock_in_data': stock_in_data.values(),
            'transfer_data': transfer_data.values(),
            'labels': labels,
        }, status.HTTP_200_OK)
    
class InventoryIndexJson(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        inventory = Inventory.objects.filter(branch=request.user.branch, status=True).values(
            'id', 'name', 'price', 'cost', 'quantity', 'reorder'
        ).order_by('name')
        return Response(inventory, status.HTTP_200_OK)

class ActivateInventory(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, product_id):
        product = get_object_or_404(Inventory, id=product_id)
        product.status=True
        product.save()
        
        ActivityLog.objects.create(
            invoice = None,
            product_transfer = None,
            branch = request.user.branch,
            user=request.user,
            action= 'activated',
            inventory=product,
            quantity=product.quantity,
            total_quantity=product.quantity
        )
        serializer = InventorySerializer(product)
        return Response(serializer.data, status.HTTP_200_OK)

class DefectiveProductList(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        defective_products = DefectiveProduct.objects.filter(branch=request.user.branch)
        
        # loss calculation
        data = request.data
        defective_id = data.get('product_id')
        quantity = data.get('quantity')       
        try:
            d_product = DefectiveProduct.objects.get(id=defective_id, branch=request.user.branch)
            product = Inventory.objects.get(product__id=d_product.product.id, branch=request.user.branch)
        except:
            return Response({'message':'Product doesnt exists'}, status.HTTP_400_BAD_REQUEST)
    
        product.quantity += quantity
        product.status = True if product.status == False else product.status
        product.save()
        
        d_product.quantity -= quantity
        d_product.save()
        
        ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= 'stock in',
            inventory=product,
            quantity=quantity,
            total_quantity=product.quantity,
            description = 'from defective products'
        )
        return Response(status.HTTP_200_OK)
    
        quantity = defective_products.aggregate(Sum('quantity'))['quantity__sum'] or 0
        price = defective_products.aggregate(Sum('product__cost'))['product__cost__sum'] or 0
        
        return render(request, 'defective_products.html', 
            {
                'total_cost': quantity * price,
                'defective_products':defective_products,
            }
        )

class BranchesInventory(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        branches_inventory = Inventory.objects.filter(status=True).values(
            'name', 'price', 'quantity', 'branch__name'
        )
        return Response(branches_inventory, status.HTTP_200_OK)

class DefectiveProductViewAdd(views.APIView):
    def get(self, request):
        defective_products = DefectiveProduct.objects.filter(branch=request.user.branch)
        quantity = defective_products.aggregate(Sum('quantity'))['quantity__sum'] or 0
        price = defective_products.aggregate(Sum('product__cost'))['product__cost__sum'] or 0
        
        return Response( 
            {
                'total_cost': quantity * price,
                'defective_products':defective_products,
            },
            status.HTTP_200_OK
        )
    # loss calculation
    def post(self, request):
        data = request.data
        
        defective_id = data['product_id']
        quantity = data['quantity']
        
        try:
            d_product = DefectiveProduct.objects.get(id=defective_id, branch=request.user.branch)
            product = Inventory.objects.get(product__id=d_product.product.id, branch=request.user.branch)
        except:
            return Response({'success': False, 'message':'Product doesnt exists'}, status.HTTP_400_BAD_REQUEST)
    
        product.quantity += quantity
        product.status = True if product.status == False else product.status
        product.save()
        
        d_product.quantity -= quantity
        d_product.save()
        
        ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= 'stock in',
            inventory=product,
            quantity=quantity,
            total_quantity=product.quantity,
            description = 'from defective products'
        )
        return Response({'success':True}, status.HTTP_200_OK)
