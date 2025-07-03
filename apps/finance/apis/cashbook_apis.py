from apps.finance.helpers.imports import *

class CashBook(APIView):
    def get(self, request, *args, **kwargs):
        Currency = Currency.objects.get(default=True)
        
        data = {"message": "GET method overridden successfully"}
        return Response(data)


class IncomeViewSet(viewsets.ModelViewSet):
    queryset = Income.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        if request.user:
            queryset = queryset.filter(branch=request.user.branch)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Income data fetched successfully",
            "count": queryset.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        if float(data.get('amount', 0)) < 0:
            return Response(
                {"error": "Amount cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category_data = data.get('category', {})
        if category_data.get('isNew', False):
            category, created = IncomeCategory.objects.get_or_create(
                name=category_data.get('text'),
                defaults={
                    'description': f"Auto-created category: {category_data.get('text')}"
                }
            )
        else:

            try:
                category = IncomeCategory.objects.get(
                    id=category_data.get('value')
                )
            except IncomeCategory.DoesNotExist:
                return Response(
                    {"error": "Selected category does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        main_category_data = data.get('main_category', {})
        try:
            main_category = IncomeCategory.objects.get(
                id=main_category_data.get('value')
            )
        except IncomeCategory.DoesNotExist:
            return Response(
                {"error": "Selected main category does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data['category'] = category.id
        data['main_category'] = main_category.id
        
        try:
            Branch.objects.get(id=data.get('branch'))
        except Branch.DoesNotExist:
            return Response(
                {"error": "Selected branch does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            User.objects.get(id=data.get('account_to'))
        except User.DoesNotExist:
            return Response(
                {"error": "Selected account does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        expense = serializer.save(
            category=category,
            main_category=main_category
        )

        response_serializer = self.get_serializer(expense)
        return Response(
            {
                "message": "Expense created successfully", 
                "data": response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        if request.user:
            queryset = queryset.filter(branch=request.user.branch)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "message": "Income data fetched successfully",
            "count": queryset.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        if float(data.get('amount', 0)) < 0:
            return Response(
                {"error": "Amount cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category_data = data.get('category', {})
        if category_data.get('isNew', False):
            category, created = ExpenseCategory.objects.get_or_create(
                name=category_data.get('text'),
                defaults={
                    'description': f"Auto-created category: {category_data.get('text')}"
                }
            )
        else:
            try:
                category = ExpenseCategory.objects.get(
                    id=category_data.get('value')
                )
            except ExpenseCategory.DoesNotExist:
                return Response(
                    {"error": "Selected category does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        main_category_data = data.get('main_category', {})
        try:
            main_category = ExpenseCategory.objects.get(
                id=main_category_data.get('value')
            )
        except ExpenseCategory.DoesNotExist:
            return Response(
                {"error": "Selected main category does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data['category'] = category.id
        data['main_category'] = main_category.id
        
        try:
            Branch.objects.get(id=data.get('branch'))
        except Branch.DoesNotExist:
            return Response(
                {"error": "Selected branch does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            User.objects.get(id=data.get('account_to'))
        except User.DoesNotExist:
            return Response(
                {"error": "Selected account does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        expense = serializer.save(
            category=category,
            main_category=main_category
        )

        response_serializer = self.get_serializer(expense)
        return Response(
            {
                "message": "Expense created successfully", 
                "data": response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    
   