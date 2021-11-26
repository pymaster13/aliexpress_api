# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime, timedelta

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from top import api, appinfo

def create_connection(db_file):
    conn = None

    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(e)

    return conn

url = 'gw.api.taobao.com'
port = 80
appkey = '32827283'
secret = '**********************'
sessionkey = '*******************************************'
sender_email = "*********.ru"
receiver_email = "*****************@yandex.ru"

req_new_orders = api.AliexpressSolutionOrderGetRequest(url, port)
req_new_orders.set_app_info(appinfo(appkey, secret))

current_page = 1
count_pages = 0

conn = create_connection('aliexpress.db')
c = conn.cursor()

c.execute(
    '''
    CREATE TABLE IF NOT EXISTS ali_order (
        id PRIMARY KEY, status, sended DEFAULT 0);'''
        )

new_orders = []

while (count_pages != current_page):   
    
    # If it is not first iteration
    if count_pages != 0:
        current_page += 1

    req_new_orders.param0 = {
    'create_date_start': (datetime.utcnow() - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S'),
    'page_size': 50,
    'current_page': current_page
    }

    response_new_orders = req_new_orders.getResponse(sessionkey)
    json_new_orders = response_new_orders['aliexpress_solution_order_get_response']['result']['target_list']['order_dto']

    for order in json_new_orders:

        c.execute(
            '''
            SELECT id, status FROM ali_order WHERE id = '%d'
            ''' % order['order_id']
        )

        order_from_db = c.fetchone()

        if not order_from_db:
            new_orders.append(order['order_id'])

            c.execute(
                """
                INSERT INTO ali_order (id, status) VALUES ('%d','%s'); 
                """ % (order['order_id'], order['order_status']))

        else:
            if order_from_db[1] != order['order_status']:

                c.execute(
                    """
                    UPDATE ali_order SET status='%s' WHERE id='%d'; 
                    """ % (order['order_status'], order['order_id']))
        
    # If it is first iteration - take count pages from api
    if count_pages == 0:
        count_pages = response_new_orders['aliexpress_solution_order_get_response']['result']['total_page']

c.execute(
    '''
    SELECT id FROM ali_order WHERE status = '%s' and sended = 0
    ''' % 'IN_CANCEL'
        )

cancelled_orders = c.fetchall()

for order in cancelled_orders:    
    c.execute(
        """
        UPDATE ali_order SET sended=1 WHERE id = '%d'; 
        """ % (long(order[0]),))

conn.commit()
c.close()
conn.close()

req_order = api.AliexpressSolutionOrderInfoGetRequest(url,port)
req_order.set_app_info(appinfo(appkey,secret))

orders = []
if new_orders:
    orders.extend(new_orders)
if cancelled_orders:
    orders.extend(cancelled_orders)

if orders:
    server = smtplib.SMTP('localhost')

    for order in orders:    
    	req_order.param1 = {}
    	req_order.param1['order_id'] = order
    	try:
    	    resp = req_order.getResponse(sessionkey)
    	    order_data = resp['aliexpress_solution_order_info_get_response']['result']['data']
    	    products = order_data['child_order_ext_info_list']['global_aeop_tp_order_product_info_dto']

    	    if order_data['order_status'] == 'IN_CANCEL':
                theme = u'Отмена заказа от Aliexpress №%s' % order
    	    else:
            	theme = u'Новый заказ от Aliexpress №%s' % order
    	    resp = req_order.getResponse(sessionkey)
    	    order_data = resp['aliexpress_solution_order_info_get_response']['result']['data']

            products_for_sku = order_data['child_order_list']['global_aeop_tp_child_order_dto'] 

    	    body = u''
    	    body += u'Никнейм покупателя: %s\n' % order_data['buyer_signer_fullname']
    	    body += u'Имя получателя: %s\n' % order_data['receipt_address']['contact_person']
    	    phone = order_data['receipt_address']['phone_country'] + order_data['receipt_address']['mobile_no']
    	    body += u'Номер телефона: %s\n' % phone
    	    body += u'Адрес доставки: %s\n\n' % order_data['receipt_address']['localized_address']    
    	    body += u'Состав заказа:\n'
    	    cost = 0.0

    	    for index, product in enumerate(products_for_sku):
                body += u'%d. Наименование товара: %s\n' % (index+1, product['product_name'])
                body += u'Код товара aliexpress: %s\n' % product['product_id']
                body += u'Код товара учет: %s\n' % product['sku_code']

		body += u'Количество: %s\n' % product['product_count']

                body += u'Цена: %s %s\n\n' % (product['product_price']['amount'], product['product_price']['currency_code'])
                cost += float(product['product_price']['amount']) * float(product['product_count'])
    
    	    try:
                body += u'Сумма заказа: %s %s' % (order_data['pay_amount_by_settlement_cur'], order_data['settlement_currency'])
    	    except:
                body += u'Сумма заказа: %.2f RUB' % cost

    	    msg = MIMEMultipart()
    	    msg['Subject'] = theme
    	    msg['From'] = sender_email
    	    msg['To'] = receiver_email
    	    plain_text = MIMEText(body, _subtype='plain', _charset='UTF-8')
    	    msg.attach(plain_text)

    	    server.sendmail(sender_email, receiver_email, msg.as_string())

    	except Exception as e:
            print(e)
	
    server.quit()
