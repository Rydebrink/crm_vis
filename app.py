from flask import Flask, render_template, flash, redirect, url_for, request, logging
import requests as api_request
import json
import functools
import collections
import operator
import datetime
import calendar
from classes.customer import Customer
from classes.deal import Deal
from classes.chart import Chart
from dateutil.parser import parse
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('PROJECT_API_KEY')

STATUS_CUSTOMER = 3
STATUS_INACTIVE = 2
STATUS_PROSPECT = 1
STATUS_IRRELEVANT = 0

AVERAGE_YEAR_TITLE = "Average deal value per year in SEK"
AVERAGE_YEAR_LABEL = "Average deal value in SEK"

AVERAGE_MONTH_TITLE = "Deals closed per month for "
AVERAGE_MONTH_LABEL = "Total number of orders won"

CUSTOMER_VALUE_TITLE = "Total value of orders won per customer for "
CUSTOMER_VALUE_LABEL = "Total value "

app = Flask(__name__, static_url_path='/static')

headers = {
    "Content-Type": "application/json",
    "Accept": "application/hal+json",
    "x-api-key": API_KEY
}


def get_api_data(headers, url):
    # First call to get first data page from the API
    response = api_request.get(
        url=url, headers=headers, data=None, verify=False)

    # Convert the response string into json data and get embedded limeobjects
    json_data = json.loads(response.text)

    limeobjects = json_data.get("_embedded").get("limeobjects")

    # Check for more data pages and get thoose too
    nextpage = json_data.get("_links").get("next")
    while nextpage is not None:
        url = nextpage["href"]
        print("hello")
        response = api_request.get(
            url=url, headers=headers, data=None, verify=False)
        json_data = json.loads(response.text)
        limeobjects += json_data.get("_embedded").get("limeobjects")
        nextpage = json_data.get("_links").get("next")

    return limeobjects


def get_deal_data(headers):
    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    params = "?_limit=50&_embed=company"
    url = base_url + params

    return get_api_data(headers, url)


def get_customer_data(headers):
    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/company/"
    params = "?_limit=50"
    url = base_url + params

    return get_api_data(headers, url)


def get_deals_for_customer(header, id):
    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/company/"
    params = str(id)+"/deal/"
    url = base_url + params
    return get_api_data(headers, url)


def filter_deal(entry, close_date):
    if entry.get("_embedded") is not None:
        company = entry.get("_embedded").get("relation_company")
        customer_id = company.get("_id")
        name = company.get("name")
        status = company.get("buyingstatus").get("key")
        www = company.get("www")
        phone = company.get("phone")
        address = company.get("postaladdress1")
        zip_code = company.get("postalzipcode")
        city = company.get("postalcity")
        country = company.get("country")
        deals = []
        customer = Customer(customer_id, name, status, www,
                            phone, address, zip_code, city, country, deals)
    else:
        customer = None
    return Deal(entry.get("_id"),
                entry.get("dealstatus").get("key"),
                entry.get("value"),
                entry.get("_descriptive"),
                close_date,
                customer)


def filter_deals(data):
    deals = []
    # import pdb
    # pdb.set_trace()
    for entry in data:
        try:
            parse(entry.get("closeddate"))
        except TypeError:
            deals.append(filter_deal(entry, None))
        else:
            deals.append(filter_deal(entry, parse(entry.get("closeddate"))))
    return deals


def filter_customers(customer_data, filtered_deals):
    customer_deals = collections.defaultdict(list)
    for deal in filtered_deals:
        if deal.customer is not None:
            customer_deals[deal.customer.customer_id].append(deal)
    customers = []
    for entry in customer_data:
        customer_id = entry.get("_id")
        name = entry.get("name") if entry.get("name") else "N/A"
        status = entry.get("buyingstatus").get("key")
        www = entry.get("www") if entry.get("www") else "N/A"
        phone = entry.get("phone") if entry.get("phone") else "N/A"
        address = entry.get("postaladdress1") if entry.get(
            "postaladdress1") else "N/A"
        zip_code = entry.get("postalzipcode") if entry.get(
            "postalzipcode") else "N/A"
        city = entry.get("postalcity") if entry.get("postalcity") else "N/A"
        country = entry.get("country") if entry.get("country") else "N/A"
        deals = customer_deals.get(customer_id)
        customers.append(Customer(customer_id, name, status,
                                  www, phone, address, zip_code, city, country, deals))
    return customers


def get_total_deals(data, data_key):
    return_data = []
    for entry in data:
        return_data.append(entry.get(data_key))
    return return_data


def get_years(data):
    years = set()
    for entry in data:
        try:
            parse(entry.get("closeddate"))
        except TypeError:
            print("No date available")
        else:
            years.add(parse(entry.get("closeddate")).year)
    return sorted(years)


def get_graph_labels(data, label_key):
    return_data = []
    for entry in data:
        return_data.append(entry.get(label_key))
    return return_data


def get_graph_data(data, data_key):
    return_data = []
    for entry in data:
        return_data.append(entry.get(data_key))
    return return_data


def get_graph_colors(colors):
    if colors <= 0:
        return []
    delta = 360/colors
    hue = delta/2
    background_color = []
    border_color = []
    for x in range(colors):
        background_color.append("hsla("+str(int(hue))+", 69%, 58%, 0.3)")
        border_color.append("hsla("+str(int(hue))+", 69%, 58%, 1)")
        hue += delta
    return [background_color, border_color]


def create_chart(data, title, label, chart_type, label_key, data_key):
    chart_labels = get_graph_labels(data, label_key)
    chart_data = get_graph_data(data, data_key)
    graph_colors = get_graph_colors(len(chart_labels))
    print(data, title, label, chart_type, label_key, data_key, graph_colors)
    return Chart(title, label, chart_type, chart_labels, chart_data, graph_colors[0], graph_colors[1])


def get_average_per_year(data):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        year = deal.closing_date.year if deal.closing_date is not None else None
        status = deal.status
        if status == "agreement" and year is not None:
            value = deal.value
            collected_data[year].append(value)
    for year in collected_data:
        count = 0
        total = 0
        for value in collected_data[year]:
            total += value
            count += 1
        collected_data[year] = round((total / count))
        return_data.append(
            {"year": year, "avg_value": collected_data[year], "total_deals": count})
    return sorted(return_data, key=operator.itemgetter("year"))


def get_average_per_month(data, year):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        deal_year = deal.closing_date.year if deal.closing_date is not None else None
        status = deal.status
        if deal_year == year and status == "agreement":
            month = deal.closing_date.month
            collected_data[month].append(1)
    for month in collected_data:
        count = 0
        for value in collected_data[month]:
            count += 1
        collected_data[month] = count
        return_data.append(
            {"month": month, "name": calendar.month_name[month], "total_deals": collected_data[month]})
    return sorted(return_data, key=operator.itemgetter("month"))


def get_customer_value(deals, year):
    deal_data = collections.defaultdict(list)
    customer_data = collections.defaultdict(set)
    return_data = []
    for deal in deals:
        customer = deal.customer
        closing_date = deal.closing_date
        if customer is not None and closing_date is not None:
            if deal.closing_date.year == year and deal.status == "agreement":
                deal_data[customer.customer_id].append(deal.value)
                customer_data[customer.customer_id].add(deal.customer.name)
    for cust in deal_data:
        total = 0
        count = 0
        for value in deal_data[cust]:
            total += value
            count += 1
        deal_data[cust] = total
        name = customer_data.get(cust).pop()
        return_data.append(
            {"customer_id": cust, "customer_name": name, "value": deal_data[cust], "total_deals": count})

    return sorted(return_data, key=operator.itemgetter("value"), reverse=True)


@ app.route('/')
def index():
    year = (subtract_years(
        datetime.datetime.now(datetime.timezone.utc), 1).year)
    data = get_deal_data(headers)
    deals = filter_deals(data)
    average_per_year = get_average_per_year(deals)
    average_per_month = get_average_per_month(
        deals, year)
    customer_value = get_customer_value(
        deals, year)
    print("NOW", customer_value)
    if len(deals) > 0:
        charts = [
            create_chart(
                average_per_year, AVERAGE_YEAR_TITLE, AVERAGE_YEAR_LABEL, "bar", "year", "avg_value"),
            create_chart(
                average_per_year, AVERAGE_YEAR_TITLE, AVERAGE_YEAR_LABEL, "pie", "year", "avg_value"),

            create_chart(
                average_per_month, AVERAGE_MONTH_TITLE + str(year), AVERAGE_MONTH_LABEL, "bar", "name", "total_deals"),
            create_chart(
                average_per_month, AVERAGE_MONTH_TITLE + str(year), AVERAGE_MONTH_LABEL, "pie", "name", "total_deals"),

            create_chart(
                customer_value, CUSTOMER_VALUE_TITLE + str(year), CUSTOMER_VALUE_LABEL, "horizontalBar", "customer_name", "value"),
            create_chart(
                customer_value, CUSTOMER_VALUE_TITLE + str(year), CUSTOMER_VALUE_LABEL, "pie", "customer_name", "value")
        ]
        return render_template('home.html', charts=charts, year=str(year))


@ app.route('/example')
def example():
    data = get_deal_data(headers)
    deals = filter_deals(data)
    deals = []
    if len(deals) > 0:
        return render_template('example.html', deals=deals)
    else:
        msg = 'No deals found'
        return render_template('example.html', error=msg)


@ app.route('/average_year')
def average_year():

    data = get_deal_data(headers)
    deals = filter_deals(data)
    if len(deals) > 0:
        average_per_year = get_average_per_year(deals)
        charts = [
            create_chart(
                average_per_year, AVERAGE_YEAR_TITLE, AVERAGE_YEAR_LABEL, "bar", "year", "avg_value"),
            create_chart(
                average_per_year, "Total deals won per year", "Total deals won", "bar", "year", "total_deals")
        ]
        print(charts)
        return render_template('average_year.html', charts=charts)
    else:
        msg = 'No deals found'
        return render_template('average_year.html', msg=msg)


@ app.route('/average_month')
def average_month_default():
    year = str(subtract_years(
        datetime.datetime.now(datetime.timezone.utc), 1).year)
    return average_month(year)


@ app.route('/average_month/<pick_year>')
def average_month(pick_year):
    year = datetime.datetime(int(pick_year), 1, 1).year

    data = get_deal_data(headers)
    deals = filter_deals(data)
    years = get_years(data)
    if len(deals) > 0:
        average_per_month = get_average_per_month(
            deals, year)
        charts = [
            # create_chart(
            #     average_per_month, AVERAGE_MONTH_TITLE + str(year), AVERAGE_MONTH_LABEL, "line", "name", "total_deals"),
            # create_chart(
            #     average_per_month, AVERAGE_MONTH_TITLE + str(year), AVERAGE_MONTH_LABEL, "pie", "name", "total_deals"),
            create_chart(
                average_per_month, AVERAGE_MONTH_TITLE + str(year), AVERAGE_MONTH_LABEL, "bar", "name", "total_deals")
        ]
        return render_template('average_month.html', deals=average_per_month, display_year=year, charts=charts, years=years)
    else:
        msg = 'No deals found'
        return render_template('average_month.html', msg=msg)


@ app.route('/customer_value')
def customer_value_default():
    year = str(subtract_years(
        datetime.datetime.now(datetime.timezone.utc), 1).year)
    return customer_value(year)


@ app.route('/customer_value/<pick_year>')
def customer_value(pick_year):

    year = datetime.datetime(int(pick_year), 1, 1).year
    data = get_deal_data(headers)
    deals = filter_deals(data)
    years = get_years(data)
    customer_value = get_customer_value(
        deals, year)
    if len(customer_value) > 0:
        charts = [
            create_chart(
                customer_value, CUSTOMER_VALUE_TITLE + str(year), CUSTOMER_VALUE_LABEL, "horizontalBar", "customer_name", "value")
        ]
        return render_template('customer_value.html', charts=charts, years=years)
    else:
        msg = 'No customers found'
        return render_template('customer_value.html', error=msg,  years=years)


def subtract_years(dt, years):
    try:
        dt = dt.replace(year=dt.year-years)
    except ValueError:
        dt = dt.replace(year=dt.year-years, day=dt.day-1)
    return dt


def set_customer_status(customer, year):
    try:
        data = []
        for deal in customer.deals:
            if deal.status == "agreement":
                if deal.closing_date > year or deal.closing_date.year == year.year:
                    # if deal.closing_date.year == year:
                    deal_status_value = STATUS_CUSTOMER
                else:
                    deal_status_value = STATUS_INACTIVE
            elif customer_status == "irrelevant":
                deal_status_value = STATUS_IRRELEVANT
            else:
                deal_status_value = STATUS_PROSPECT
            data.append(deal_status_value)

        status = max(data)
        if status == STATUS_CUSTOMER:
            return "Customer"
        elif status == STATUS_INACTIVE:
            return "Inactive"
        elif status == STATUS_IRRELEVANT:
            return "Irrelevant"
        elif status == STATUS_PROSPECT:
            return "Prospect"
        else:
            return "Unknown status"
    except TypeError:
        return "Irrelevant" if customer.status == "irrelevant" else "Prospect"


def get_customer_status(customers):
    return_data = []
    # last_year = subtract_years(
    #     datetime.datetime.now(datetime.timezone.utc), 1).year
    last_year = subtract_years(
        datetime.datetime.now(datetime.timezone.utc), 1)
    for customer in customers:
        status = set_customer_status(customer, last_year)
        total_value = customer.get_customer_value()
        try:
            latest_deal = sorted(customer.deals, key=operator.attrgetter(
                "closing_date"), reverse=True)[0].closing_date.strftime("%Y-%m-%d")
        except TypeError:
            latest_deal = "N/A"
        except AttributeError:
            latest_deal = "N/A"
        return_data.append(
            {"id": customer.customer_id, "customer_name": customer.name, "customer_status": status, "total_value": format_value(total_value), "latest_deal": latest_deal})
    return_data.append(
        {"id": customer.customer_id, "customer_name": customer.name, "customer_status": "Irrelevant", "total_value": format_value(total_value), "latest_deal": latest_deal})
    return return_data


@ app.route('/customer_status')
def customer_status():
    year = str(subtract_years(
        datetime.datetime.now(datetime.timezone.utc), 1).year)

    customer_data = get_customer_data(headers)
    deal_data = get_deal_data(headers)
    customers = filter_customers(customer_data, filter_deals(deal_data))
    if len(customers) > 0:
        customers_status = get_customer_status(customers)
        return render_template('customer_status.html', customers=customers_status)
    else:
        msg = 'No customers found'
        return render_template('customer_status.html', error=msg)


def format_deals(deals):
    return_data = []
    for deal in deals:
        deal.value = format_value(deal.value)
        deal.status = deal.status.capitalize()
        deal.closing_date = deal.closing_date.strftime("%Y-%m-%d")
        return_data.append(deal)
    return return_data


def format_value(number):
    return("{:,.2f} SEK".format(number))


@ app.route('/customer/<id>')
def customer_info(id):
    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/company/"
    params = id+"/"
    url = base_url + params
    response = api_request.get(
        url=url, headers=headers, data=None, verify=False)

    response_customer = [json.loads(response.text)]

    url += "deal/"
    response_deals = get_api_data(headers=headers, url=url)

    if len(response_customer) > 0:
        deal_info = filter_deals(response_deals)
        customer_info = filter_customers(response_customer, deal_info)
        customer = customer_info[0]
        customer.deals = deal_info
        total = customer.get_customer_value()
        deals_formatted = format_deals(deal_info)
        return render_template('customer_info.html', customer=customer, deals=deals_formatted, total_value=format_value(total), total_orders=len(deal_info))
    else:
        msg = 'No deals found'
        return render_template('customer_info.html', msg=msg)

# You can add more pages to your app, like this:
#
# @app.route('/myroute')
# def myroute():
# 	mydata = [{'name': 'apple'}, {'name': 'mango'}, {'name': 'banana'}]
# 	return render_template('mytemplate.html', items=mydata)
#
# You also have to create the mytemplate.html page inside the 'templates'-folder to be rendered
# And then add a link to your page in the _navbar.html-file, located in templates/includes/


# DEBUGGING
# If you want to debug your app, one of the ways you can do that is to use:
# import pdb; pdb.set_trace()
# Add that line of code anywhere, and it will act as a breakpoint and halt your application


if __name__ == '__main__':
    app.secret_key = 'somethingsecret'
    app.run(debug=True)
