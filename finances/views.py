import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from .logic import parse_item_library, split_logic   # we will move your functions here

def index(request):
    return render(request, "finances/index.html")

def run_report(request):
    if request.method == "POST":
        raw_file = request.FILES.get("raw_file")
        key_file = request.FILES.get("key_file")

        if not raw_file or not key_file:
            return HttpResponse("Missing files.")

        raw_df = pd.read_csv(raw_file)
        key_df = pd.read_csv(key_file)

        library = parse_item_library(key_df)
        final_report = split_logic(raw_df, library)

        # Convert tables to HTML
        summary = final_report.groupby("Min")[["Gross", "Fees", "Net"]].sum().to_html()
        daily = final_report.groupby("Date")[["Gross", "Fees", "Net"]].sum().to_html()

        # Convert CSV for download
        csv_data = final_report.to_csv(index=False)

        return render(request, "finances/results.html", {
            "summary": summary,
            "daily": daily,
            "csv_data": csv_data,
        })

def download_csv(request):
    csv_data = request.POST.get("csv_data")
    response = HttpResponse(csv_data, content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="Square_Final_Reconciled.csv"'
    return response