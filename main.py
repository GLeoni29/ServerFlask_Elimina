from flask import Flask, render_template, request
from google.cloud import firestore
import time
from datetime import datetime


# apertura connessione DB Firestore
db = 'test1'
coll = 'Arduino1'
db = firestore.Client.from_service_account_json('credentials.json', database=db)



'''avvio istanza flask'''
app = Flask(__name__)




# Variabile per tenere traccia del tempo di apertura dello sportello
sportello_aperto_da = None
stato_allarme = False
lista_messaggi = []


def controlla_condizioni(temperatura, sportello_aperto):
    global lista_messaggi
    global sportello_aperto_da
    global stato_allarme

    if sportello_aperto == '1': #0 : sportello è aperto
        if sportello_aperto_da is None:
            sportello_aperto_da = time.time()
            allarme_sportello = False
        elif time.time() - sportello_aperto_da > 30:
            allarme_sportello = True
        else:
            allarme_sportello = False
    else:
        sportello_aperto_da = None
        allarme_sportello = False

    #if temperatura < 20 or temperatura > 25:
        # Attiva LED e cicalino se la temperatura è fuori range
        #ser.write(b'L')
        #ser.write(b'C')
        ####
        #allarme_temperatura = True
    #else:
        #ser.write(b'O')
        #allarme_temperatura = False

    #if allarme_temperatura or allarme_sportello:
    if allarme_sportello and not stato_allarme:
        stato_allarme = True
        #return "LEDandBUZZER_ON" # accendi led e buzzer
        lista_messaggi.append("LEDandBUZZER_ON")
    elif not allarme_sportello and stato_allarme:
        stato_allarme = False
        #return "LEDandBUZZER_OFF" # spegni led e buzzer
        lista_messaggi.append("LEDandBUZZER_OFF")
    elif allarme_sportello and stato_allarme:
        pass #scrivi che in questi casi non sia append nessun messaggio
        #return "" # messaggio vuoto
    elif not allarme_sportello and not stato_allarme:
        pass
        #return "" # messaggio vuoto


''' RECUPERA DATI DA CLIENT_SERVER (arduino)'''
@app.route('/dati', methods=['POST'])
def ricevi_dati():
    #data = request.json
    dataora = request.form.get('dataora')
    temperatura = request.form.get('temperatura')
    sportello = request.form.get('sportello')
    #temperatura = data['temperatura']
    #sportello = data['sportello']

    # Controlla le condizioni
    #messaggio = controlla_condizioni(temperatura, sportello)
    controlla_condizioni(temperatura, sportello)

    # Salva i dati su BigQuery
    row_to_insert = [{
        "dataora": dataora,
        "temperatura": temperatura,
        "sportello": sportello
    }]

    # Salva i dati su Firestore
    doc_ref = db.collection(coll).document() # id di default
    #doc_ref.set({'nome': 'sensor', 'value': [{'val': 2}]})
    doc_ref.set({"dataora": dataora,"temperatura": temperatura,"sportello": sportello}) # imposto documeto
    #print(doc_ref.get().id)
    print(doc_ref.get())

    return "Dati salvati", 200




# ------ HOME ------
@app.route('/')
def home():
    return render_template('index.html')


# ------ AREA MONITOR ------
@app.route('/area_monitor')
def area_monitor():
    global sportello_aperto_da

    db = 'test1'
    coll = 'Arduino1'
    db = firestore.Client.from_service_account_json('credentials.json', database=db)

    # Inizializza il client Firestore utilizzando il file delle credenziali.
    #db = firestore.Client.from_service_account_json('credentials.json')

    # Riferimento alla collezione e alla query su Firestore
    collection_ref = db.collection(coll)

    # Ordina i documenti per campo 'dataora' in ordine decrescente e limita a 1
    docs = collection_ref.order_by('dataora', direction=firestore.Query.DESCENDING).limit(1).stream()

    # Ottieni l'ultimo record inserito
    row = None
    for doc in docs:
        row = doc.to_dict()
        break  # Prendi solo il primo documento

    if row is None:
        print("Nessun dato disponibile.")
        return render_template('area_monitor.html', stato="ERRORE - Nessun dato", temperatura=None, sportello=None, orario=None)


    # Stato di monitoraggio
    stato = "ok con sportello chiuso"
    if float(row['temperatura']) < 20 or float(row['temperatura']) > 30:
        stato = "allarme temperatura"
    elif int(row['sportello']) == 1:
        if sportello_aperto_da is None:
            sportello_aperto_da = time.time()
        tempo_apertura = time.time() - sportello_aperto_da
        if tempo_apertura > 30:
            stato = "sportello aperto da più di 30 sec"
        else:
            stato = f"ok con sportello aperto da {int(tempo_apertura)} secondi"
    else:
        sportello_aperto_da = None

    # Estrarre orario dal campo 'dataora'
    dataora = datetime.strptime(row['dataora'], '%Y-%m-%d %H:%M:%S.%f')
    orario = dataora.strftime('%H:%M:%S')



    # Renderizza il template con i dati
    return render_template('area_monitor.html', stato=stato, temperatura=row['temperatura'], sportello=row['sportello'],orario=orario)


# ------ AREA ANALISI ------
@app.route('/area_analisi')
def area_analisi():
    db = 'test1'
    coll = 'Arduino1'

    # Inizializza il client Firestore utilizzando il file delle credenziali.
    db = firestore.Client.from_service_account_json('credentials.json', database=db)

    # Ottieni la data corrente
    oggi = datetime.now().date()
    dataora = str(datetime(oggi.year, oggi.month, oggi.day))
    print("tipo dataora: ", type(dataora))

    # Query su Firestore per ottenere tutti i documenti di oggi, ordinati per 'dataora'
    collection_ref = db.collection(coll)
    docs = collection_ref.where('dataora', '>=', dataora).order_by('dataora', direction=firestore.Query.ASCENDING).stream()

    # Liste per i dati di temperatura e sportello
    dati_temperatura = [['DataOra', 'Temperatura']]
    dati_sportello = [['DataOra', 'Sportello']]

    # Itera su ogni documento restituito dalla query
    for doc in docs:
        row = doc.to_dict()
        dataora = datetime.strptime(row['dataora'] ,'%Y-%m-%d %H:%M:%S.%f')
        dataora = dataora.strftime('%H:%M:%S')
        dati_temperatura.append([dataora, float(row['temperatura'])])
        dati_sportello.append([dataora, int(row['sportello'])])



    print("dati temperatura: ", dati_temperatura)
    print("dati sportello: ", dati_sportello)

    # Renderizza il template con i dati
    return render_template('area_analisi.html', dati_temperatura=dati_temperatura, dati_sportello=dati_sportello)


###########################################################################
@app.route('/filtra_dati', methods=['POST'])
def filtra_dati():
    action = request.form.get('action')  # Identifica quale pulsante è stato premuto


    data = request.form.get('data')
    orario_inizio = request.form.get('orario_inizio')
    orario_fine = request.form.get('orario_fine')

    # Inizializza il client Firestore
    #db = firestore.Client.from_service_account_json('credentials.json')
    db = 'test1'
    coll = 'Arduino1'
    db = firestore.Client.from_service_account_json('credentials.json', database=db)

    # Riferimento alla collezione
    collection_ref = db.collection(coll)

    if data == "":
        #si intende oggi
        data = str(datetime.now().date())

    dataora_inizio = str(datetime.strptime(f"{data} {orario_inizio}:00.0", '%Y-%m-%d %H:%M:%S.%f'))
    dataora_fine = str(datetime.strptime(f"{data} {orario_fine}:59.0", '%Y-%m-%d %H:%M:%S.%f'))

    # Esegui la query Firestore
    docs = (collection_ref.where('dataora', '>=', dataora_inizio)\
            .where('dataora', '<=', dataora_fine)\
            .order_by('dataora', direction=firestore.Query.ASCENDING)).stream()

    print("docs: ", docs)
    print("tipo docs: ", type(docs))

    # Liste per i dati di temperatura e sportello
    dati_temperatura = [['DataOra', 'Temperatura']]
    dati_sportello = [['DataOra', 'Sportello']]

    # Itera su ogni documento restituito dalla query
    docs_list = list(docs)

    # Verifica se la lista è vuota
    if not docs_list:
        print("Nessun documento trovato.")
        dati_temperatura.append(["", 0])
        dati_sportello.append(["", 0.5])

        messaggio = "errore"

        return render_template('area_analisi.html', dati_temperatura=dati_temperatura, dati_sportello=dati_sportello,
                          messaggio=messaggio)

    else:
        # Ottieni il primo documento
        for doc in docs_list:
            row = doc.to_dict()
            dataora = datetime.strptime(row['dataora'], '%Y-%m-%d %H:%M:%S.%f')
            dataora = dataora.strftime('%H:%M:%S')
            dati_temperatura.append([dataora, float(row['temperatura'])])
            dati_sportello.append([dataora, int(row['sportello'])])

        data = data.split('-')
        messaggio = f"Dati riferiti al {data[2]}-{data[1]}-{data[0]} {orario_inizio}-{orario_fine}"

        return render_template('area_analisi.html', dati_temperatura=dati_temperatura, dati_sportello=dati_sportello, messaggio=messaggio)



# ----- AREA TEST -----
@app.route('/area_test')
def area_test():
    return render_template('area_test.html')

@app.route('/test_led_on')
def test_led_on():
    print("test on")
    global lista_messaggi
    print("lista on ", lista_messaggi)
    lista_messaggi.append("LED_ON")
    return render_template('area_test.html')

@app.route('/test_led_off')
def test_led_off():
    print("test_off")
    global lista_messaggi
    print("lista off ", str(lista_messaggi))
    lista_messaggi.append("LED_OFF")
    return render_template('area_test.html')

@app.route('/test_buzzer_on')
def test_buzzer_on():
    global lista_messaggi
    lista_messaggi.append("BUZZER_ON")
    return render_template('area_test.html')

@app.route('/test_buzzer_off')
def test_buzzer_off():
    global lista_messaggi
    lista_messaggi.append("BUZZER_OFF")
    return render_template('area_test.html')

@app.route('/test_led_e_buzzer_on')
def test_led_e_buzzer_on():
    global lista_messaggi
    lista_messaggi.append("LEDandBUZZER_ON")
    return render_template('area_test.html')

@app.route('/test_led_e_buzzer_off')
def test_led_e_buzzer_off():
    global lista_messaggi
    lista_messaggi.append("LEDandBUZZER_OFF")
    return render_template('area_test.html')


def check_messaggio(lista_messaggi):
    if len(lista_messaggi) == 1:
        messaggio = lista_messaggi[0]
        lista_messaggi.pop()
        print("lista ", lista_messaggi)
    else:
        messaggio = ""
    return messaggio

@app.route('/invia_messaggio', methods=['POST'])
def invia_messaggio():
    global lista_messaggi
    messaggio = check_messaggio(lista_messaggi)
    return messaggio





if __name__ == '__main__':
    project_id = 'pcloud-24-08-2024'
    region = 'europe-west12'
    db_id = 'test2'
    table = 'table2'
    #create_dataset(project_id,db_id,region)
    #create_table(project_id,db_id,table)
    # query = f'DROP TABLE {table_full_id}'

    app.run(host='0.0.0.0', port=80, debug=True)


    '''client = bigquery.Client.from_service_account_json('credentials.json')
    table_full_id = "pcloud-24-08-2024.test2.table2"
    # Ottieni l'ultimo record inserito
    #query = f'SELECT * FROM {table_full_id} WHERE DATE(dataora) = CURRENT_DATE() ORDER BY dataora ASC '

    oggi_completo = datetime.now().isoformat()
    print("tipo oggi_completo: ", type(oggi_completo))
    print(oggi_completo)
    oggi = datetime.fromisoformat(oggi_completo)
    print("oggi: ", oggi.date())
    print("tipo_oggi: ", type(oggi.date()))
    data_str = oggi.date().strftime('%Y-%m-%d')

    query = f'SELECT * FROM {table_full_id} WHERE DATE(dataora) = DATE("{data_str}") ORDER BY dataora ASC '
    


    query_job = client.query(query)
    # row = list(query_job.result())[0]

    rows = list(query_job.result())
    for r in rows:
        print(r)
        #print(r["dataora"].date())
        #print(type(r["dataora"].date()))
        #print()'''

    '''for row in rows:
        dataora = row['dataora'].strftime("%H:%M:%S")

        #dt = datetime.strptime(dataora, "%Y-%m-%d %H:%M:%S.%f")

        # Estrai solo l'orario
        #time_only = dt.time()

        print(row['dataora'])
        print(dataora)
        print()
        #print(type(dataora))'''