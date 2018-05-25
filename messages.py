import json
import cryptotools as cryptotools

nonce = lambda: cryptotools.generate_nodeid()

class InvalidSignatureError(Exception):
    pass

class InvalidNonceError(Exception):
    pass

def make_envelope(msgtype, msg, nodeid): #Собираю протокол
    msg['nodeid'] = nodeid
    msg['nonce'] =  nonce()
    envelope = {'data': msg,
                'msgtype': msgtype}
    return json.dumps(envelope) # еще раз сериализуем

# ------

def create_hello(nodeid, version): #Сообщение hello  - для знакомства с другими участниками сети.
    msg = {'version': version}
    return make_envelope("hello", msg, nodeid)

def create_addr(nodeid, nodes): #Сообщение addr -рассказываю пиру о моих пирах
    msg = {'nodes': nodes}
    return make_envelope("addr", msg, nodeid)

def create_ping(nodeid):  #Сообщение ping - о достижимости узла
    msg = {}
    return make_envelope("ping", msg, nodeid)

def create_pong(nodeid): #Сообщение pong - ответ о достижимости
    msg = {}
    return make_envelope("pong", msg, nodeid)

def create_block(nodeid, block): #Сообщение block - отправка всем пирам новый блок
    msg = {'block': block}
    return make_envelope("getBlock", msg, nodeid)

def chech_auth(nodeid, auth):
    msg = {'auth': auth}
    return make_envelope("checkAuth", msg, nodeid)

def send_correct(nodeid, correct):
    msg = {'correct': correct}
    return make_envelope("correct", msg, nodeid)

def search(nodeid, filter):
    msg = {'filter': filter}
    return make_envelope("filter", msg, nodeid)

def send_searchResult(nodeid, result):
    msg = {'result': result}
    return make_envelope("searchResult", msg, nodeid)

# -------

def read_envelope(message): # Читаю полученно сообщени и возвращаю в формат json, чтобы получить из него mesagetype
    message = message.decode('utf8')
    return json.loads(message)

def read_message(message): # Разбираю пришедшее сообщение на отдельные составляющие и возвращаю данные
    message = message.decode('utf8')
    envelope = json.loads(message)
    return envelope['data']
