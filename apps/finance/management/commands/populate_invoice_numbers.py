from django.core.management.base import BaseCommand
from django.db import transaction
from apps.finance.models import Invoice  
from apps.company.models import Branch  # Adjust import path as needed


class Command(BaseCommand):
    help = 'Populate invoice numbers for all branches except admin-related ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Get all branches except admin-related ones
        excluded_branches = Branch.objects.filter(
            name__icontains='admin'
        ).union(
            Branch.objects.filter(name__icontains='administration')
        )
        
        eligible_branches = Branch.objects.exclude(
            id__in=excluded_branches.values_list('id', flat=True)
        )

        self.stdout.write(f"Found {eligible_branches.count()} eligible branches")
        
        if excluded_branches.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Excluded branches: {', '.join(excluded_branches.values_list('name', flat=True))}"
                )
            )

        total_updated = 0

        for branch in eligible_branches:
            self.stdout.write(f"\nProcessing branch: {branch.name}")
            
            # Get all invoices for this branch that don't have invoice numbers
            # ordered by issue_date (first day of selling)
            invoices_without_numbers = Invoice.objects.filter(
                branch=branch,
                invoice_number__isnull=True
            ).order_by('issue_date', 'id')
            
            if not invoices_without_numbers.exists():
                self.stdout.write(f"  No invoices without numbers found for {branch.name}")
                continue

            # Get the highest existing invoice number for this branch
            last_invoice = Invoice.objects.filter(
                branch=branch,
                invoice_number__isnull=False
            ).order_by('-id').first()
            
            if last_invoice and last_invoice.invoice_number:
                try:
                    # Extract number from format like "INVBranchName-123"
                    last_number = int(last_invoice.invoice_number.split('-')[-1])
                    next_number = last_number + 1
                except (ValueError, IndexError):
                    next_number = 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Could not parse existing invoice number format, starting from 1"
                        )
                    )
            else:
                next_number = 1

            self.stdout.write(f"  Starting invoice numbering from: {next_number}")
            self.stdout.write(f"  Invoices to update: {invoices_without_numbers.count()}")

            if not dry_run:
                with transaction.atomic():
                    for invoice in invoices_without_numbers:
                        invoice_number = f"INV{branch.name}-{next_number}"
                        invoice.invoice_number = invoice_number
                        invoice.save(update_fields=['invoice_number'])
                        next_number += 1
                        total_updated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Updated {invoices_without_numbers.count()} invoices for {branch.name}"
                    )
                )
            else:
                # Show what would be updated in dry run
                for i, invoice in enumerate(invoices_without_numbers[:5]):  # Show first 5
                    invoice_number = f"INV{branch.name}-{next_number + i}"
                    self.stdout.write(f"    Invoice ID {invoice.id} -> {invoice_number}")
                
                if invoices_without_numbers.count() > 5:
                    self.stdout.write(f"    ... and {invoices_without_numbers.count() - 5} more")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN COMPLETE - Would have updated invoices across all branches"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSUCCESS: Updated {total_updated} invoice numbers across all eligible branches"
                )
            )