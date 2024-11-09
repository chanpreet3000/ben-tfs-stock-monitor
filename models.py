from typing import List


class ProductOptions:
    def __init__(self, name: str, stock_level: int, is_in_stock: bool, product_code: str,
                 formatted_price: str, product_url: str):
        self.name = name
        self.stock_level = stock_level
        self.is_in_stock = is_in_stock
        self.product_code = product_code
        self.formatted_price = formatted_price
        self.product_url = product_url

    def to_dict(self):
        return {
            'name': self.name,
            'stock_level': self.stock_level,
            'is_in_stock': self.is_in_stock,
            'product_code': self.product_code,
            'formatted_price': self.formatted_price,
            'product_url': self.product_url
        }

    def __str__(self):
        return self.to_dict().__str__()

    def __repr__(self):
        return self.__str__()


class ProductData:
    def __init__(self, name: str, product_code: str, options: List[ProductOptions],
                 product_url: str, ean: str, image_url: str):
        self.name = name
        self.product_code = product_code
        self.options = options
        self.product_url = product_url
        self.ean = ean
        self.image_url = image_url

    def to_dict(self):
        return {
            'name': self.name,
            'product_code': self.product_code,
            'options': [option.to_dict() for option in self.options],
            'product_url': self.product_url,
            'ean': self.ean,
            'image_url': self.image_url
        }

    def __str__(self):
        return self.to_dict().__str__()

    def __repr__(self):
        return self.__str__()
