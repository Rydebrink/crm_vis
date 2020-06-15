class Customer:
    def __init__(self, customer_id, name, status, www, phone, address, zip_code, city, country, deals):
        self.customer_id = customer_id
        self.name = name
        self.status = status
        self.www = www
        self.phone = phone
        self.address = address
        self.zip_code = zip_code
        self.city = city
        self.country = country
        self.deals = deals

    def get_customer_value(self):
        total = 0
        if self.deals is None:
            return 0
        for deal in self.deals:
            if deal.status == "agreement":
                total += deal.value
        print(total)
        return total
