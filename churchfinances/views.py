from io import BytesIO

import pandas as pd
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from .forms import UploadForm
from .models import ImportBatch, Transaction
from .services import importers


def _read_upload(batch):
    path = batch.uploaded_file.path
    is_excel = path.lower().endswith(('.xlsx', '.xls'))
    if batch.source == 'square':
        return pd.read_excel(path, sheet_name=0) if is_excel else pd.read_csv(path)
    # Stripe: use the itemised reconciliation-style sheet if this is a
    # multi-sheet workbook like your existing Stripe export; otherwise
    # assume a flat CSV/sheet with the same columns.
    if is_excel:
        xl = pd.ExcelFile(path)
        sheet = next((s for s in xl.sheet_names if 'itemised' in s.lower() or 'reconcil' in s.lower()), xl.sheet_names[0])
        return xl.parse(sheet)
    return pd.read_csv(path)


@staff_member_required
def upload_view(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            batch = form.save()
            try:
                df = _read_upload(batch)
                if batch.source == 'square':
                    count = importers.import_square(df, batch)
                else:
                    count = importers.import_stripe(df, batch)
                batch.row_count = count
                batch.save(update_fields=['row_count'])
            except Exception as e:
                batch.delete()
                form.add_error(None, f"Could not process that file: {e}")
            else:
                return redirect('churchfinances:report', batch_id=batch.id)
    else:
        form = UploadForm()

    return render(request, 'churchfinances/upload.html', {
        'form': form,
        'batches': ImportBatch.objects.all()[:15],
    })


def _report_context(batch, qs):
    by_ministry = qs.values('ministry').annotate(
        gross=Sum('gross'), fees=Sum('fees'), net=Sum('net'), qty=Sum('qty')
    ).order_by('ministry')
    by_day = qs.values('date').annotate(
        gross=Sum('gross'), fees=Sum('fees'), net=Sum('net')
    ).order_by('date')
    by_item = qs.values('ministry', 'item').annotate(
        gross=Sum('gross'), fees=Sum('fees'), net=Sum('net'), qty=Sum('qty')
    ).order_by('ministry', 'item')
    totals = qs.aggregate(gross=Sum('gross'), fees=Sum('fees'), net=Sum('net'))
    return {
        'batch': batch, 'transactions': qs.order_by('date', 'ministry'),
        'by_ministry': by_ministry, 'by_day': by_day, 'by_item': by_item,
        'totals': totals,
    }


@staff_member_required
def report_view(request, batch_id=None):
    batches = ImportBatch.objects.all()
    batch = get_object_or_404(ImportBatch, id=batch_id) if batch_id else batches.first()
    if batch is None:
        return render(request, 'churchfinances/upload.html', {'form': UploadForm(), 'batches': []})

    qs = Transaction.objects.filter(batch=batch)
    ministry = request.GET.get('ministry') or ''
    if ministry:
        qs = qs.filter(ministry=ministry)

    ministries = Transaction.objects.filter(batch=batch).values_list('ministry', flat=True).distinct().order_by('ministry')

    context = _report_context(batch, qs)
    context.update({'batches': batches, 'ministries': ministries, 'selected_ministry': ministry})
    return render(request, 'churchfinances/report.html', context)


@staff_member_required
def report_pdf_view(request, batch_id):
    batch = get_object_or_404(ImportBatch, id=batch_id)
    qs = Transaction.objects.filter(batch=batch)
    ministry = request.GET.get('ministry') or ''
    if ministry:
        qs = qs.filter(ministry=ministry)

    context = _report_context(batch, qs)
    context['selected_ministry'] = ministry
    html = render_to_string('churchfinances/report_pdf.html', context)

    result = BytesIO()
    pisa.CreatePDF(html, dest=result)

    safe_label = batch.label.replace(' ', '_')
    filename = f"{batch.get_source_display()}_{safe_label}.pdf"
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
