from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine, select, MetaData, Table
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only

from models import Base, Order, Log
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)


# These decorators allow you to use g.session to access the database inside the request code
@app.before_request
def create_session():
    g.session = scoped_session(
        DBSession)  # g is an "application global" https://flask.palletsprojects.com/en/1.1.x/api/#application-globals


@app.teardown_appcontext
def shutdown_session(response_or_exc):
    g.session.commit()
    g.session.remove()


"""
-------- Helper methods (feel free to add your own!) -------
"""


def l_message(d):
    # Takes input dictionary d and writes it to the Log table
    log=Log(message=json.dumps(d))
    g.session.add(log)
    g.session.commit()

"""
---------------- Endpoints ----------------
"""


@app.route('/trade', methods=['POST'])
def trade():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print(f"content = {json.dumps(content)}")
        columns = ["sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform"]
        fields = ["sig", "payload"]
        error = False
        for field in fields:
            if not field in content.keys():
                print(f"{field} not received by Trade")
                print(json.dumps(content))
                l_message(content)
                return jsonify(False)

        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print(f"{column} not received by Trade")
                error = True
        if error:
            print(json.dumps(content))
            l_message(content)
            return jsonify(False)

        signature = content.get("sig")
        payload = json.dumps(content['payload'])
        #print(payload)
        payload_content=content.get('payload')
        sender_pk = payload_content.get("sender_pk")
        receiver_pk = payload_content.get("receiver_pk")
        buy_currency=payload_content.get("buy_currency")
        sell_currency = payload_content.get("sell_currency")
        buy_amount = payload_content.get("buy_amount")
        sell_amount = payload_content.get("sell_amount")
        platform = payload_content.get("platform")
        if platform == 'Ethereum':

            eth_encoded_msg = eth_account.messages.encode_defunct(text=payload)
            if eth_account.Account.recover_message(eth_encoded_msg,signature=signature) == sender_pk:
                # print("Eth sig verifies!")
                new_order = Order(sender_pk=sender_pk, receiver_pk=receiver_pk,
                                  buy_currency=buy_currency,sell_currency=sell_currency,
                                  buy_amount=buy_amount, sell_amount=sell_amount, signature=signature)
                g.session.add(new_order)

                g.session.commit()
                return jsonify(True)
            else:
                l_message(content)
                return jsonify(False)
        elif platform == 'Algorand':
            #platform is Algorand
            if algosdk.util.verify_bytes(payload.encode('utf-8'),signature, sender_pk):
            #if algosdk.util.verify_bytes(msg.encode('utf-8'), signature, pk):
                new_order = Order(sender_pk=sender_pk, receiver_pk=receiver_pk,
                                  buy_currency=buy_currency,sell_currency=sell_currency,
                                  buy_amount=buy_amount, sell_amount=sell_amount, signature=signature)
                g.session.add(new_order)
                g.session.commit()
                return jsonify(True)
            else:
                l_message(content)
                return jsonify(False)
        # Your code here
        # Note that you can access the database session using g.session


@app.route('/order_book')
def order_book():
    # Your code here
    # Note that you can access the database session using g.session
    orders = g.session.query(Order).filter().all()
    lst=[]

    for o in orders:
        order = {}
        order['sender_pk'] = o.sender_pk
        order['receiver_pk'] = o.receiver_pk
        order['buy_currency'] = o.buy_currency
        order['sell_currency'] = o.sell_currency
        order['buy_amount'] = o.buy_amount
        order['sell_amount'] = o.sell_amount
        order['signature'] = o.signature
        lst.append(order)
    result = {}
    result['data']=lst
    return jsonify(result)


if __name__ == '__main__':
    app.run(port='5002')
