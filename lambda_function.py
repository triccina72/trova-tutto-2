# -*- coding: utf-8 -*-
# --- TROVA TUTTO V7.7 BASE STABILE + AIUTO ---

import logging
import os
import boto3
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name

# --- CONFIGURAZIONE ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME', 'MemoriaOggetti')
REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

# --- FUNZIONI DATABASE ---
def get_memoria(user_id):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'id': user_id})
        return response.get('Item', {}).get('attributes', {})
    except Exception as e:
        logger.error(f"Errore lettura DB: {e}")
        return {}

def salva_memoria(user_id, attributi):
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={'id': user_id, 'attributes': attributi})
    except Exception as e:
        logger.error(f"Errore scrittura DB: {e}")

# --- PULIZIA TESTO ---
def pulisci_testo(t):
    if not t:
        return ""
    t = str(t).lower().strip()
    spazzatura = [
        "chiedi a trova tutto di ", "chiedi a trova tutto ", "di a trova tutto di ",
        "apri trova tutto e ", "quando sono le ", "quando sono ", "quando e la ",
        "quando e il ", "quando e ", "quando ", "ricordami che sto mettendo ",
        "ricordami che metto ", "ricorda che metto ", "segna che ho messo ",
        "segna che metto ", "segna che lascio ", "segna che sono ", "che ho messo ",
        "che metto ", "che lascio ", "che appoggio ", "voglio salvare ",
        "voglio mettere via ", "voglio mettere ", "voglio posare ", "devo posare ",
        "devo mettere via ", "devo mettere ", "devo sistemare ", "sto mettendo via ",
        "sto mettendo ", "sto posando ", "sto riponendo ", "tieni a mente ",
        "non dimenticare ", "segna la posizione ", "memorizza ", "mettere a posto ",
        "mettere via ", "di mettere a posto ", "di mettere via ", "metti a posto ",
        "metti via ", "mi mettere via ", "di mettere ", "di salvare ", "di lasciare ",
        "di appoggiare ", "di riporre ", "di segnare ", "di ricordare ", "salvami ",
        "salvata ", "salvare ", "salva ", "metti ", "metto ", "mettere ", "posa ",
        "poso ", "appoggia ", "appoggio ", "lascia ", "lascio ", "mollo ",
        "butta ", "infila ", "incastra ", "nascondo ", "sistemo ", "segna ", "ricordami ",
        "ricorda ", "archivio ", "trova ", "cerca ", "dov'e ", "dove sono ",
        "dove sta ", "dove stanno ", "fammi la ", "leggi la ", "dimmi la ",
        "quali sono ", "quali ", "cosa c'e ", "cosa ho messo ", "leggi ", "controlla ",
        "li ", "qui ", "via ", "a posto ", "di ", "mi "
    ]
    pulito = False
    while not pulito:
        pulito = True
        for p in spazzatura:
            if t.startswith(p):
                t = t[len(p):].strip()
                pulito = False
                break
    suffissi = [" sono", " e", " sta", " si trova", " si trovano", " dov'e", " dove sono", " dove sta", " punto interrogativo", " punto", " interrogativo", " li", " qui"]
    for s in suffissi:
        if t.endswith(s):
            t = t[:-len(s)].strip()
    return t

def pulisci_per_ricerca(t):
    t = pulisci_testo(t)
    possessivi = ["mio ", "mia ", "miei ", "mie ", "tuo ", "tua ", "tuoi ", "tue ", "il ", "lo ", "la ", "i ", "a ", "gli ", "le ", "in ", "i ", "l'"]
    for p in possessivi:
        t = t.replace(p, "")
    return t.strip()

def get_radice(frase):
    if not frase: return ""
    p = str(frase).lower().strip().replace("h", "")
    art = ["il ", "lo ", "la ", "i ", "gli ", "le ", "l'"]
    for a in art:
        if p.startswith(a): p = p[len(a):].strip()
    parole = p.split()
    radici = []
    for w in parole:
        if len(w) > 4:
            radici.append(w[:-1])
        else:
            radici.append(w)
    return " ".join(radici)

def calcola_grammatica(t):
    t = str(t).lower().strip()
    if t.startswith(("le ", "delle ", "tutte le ")): return "sono", "le", "le"
    if t.startswith(("i ", "gli ", "dei ", "tutti i ")): return "sono", "li", "li"
    if t.startswith(("la ", "una ", "quella ")): return "e", "la", "la"
    if t.endswith("i") and len(t) > 3 and not t.startswith(("il ", "un ", "lo ")):
        return "sono", "li", "li"
    return "e", "lo", "lo"

def formatta_risposta_luogo(verbo, luogo_raw):
    l = str(luogo_raw).replace("|IMP", "").lower().strip()
    prep_art = ("nel ", "nella ", "nell'", "nello ", "nei ", "negli ", "nelle ", "sul ", "sulla ", "sullo ", "sull'", "sui ", "sugli ", "sulle ", "al ", "il ", "a ", "alla ", "allo ", "all'", "ai ", "agli ", "alle ")
    preposizioni = ("in ", "su ", "a ", "da ", "sotto ", "sopra ", "dietro ", "dentro ", "vicino ", "il ", "alle ", "l'", "verso ", "tra ", "fra ")
    if len(l) > 0 and (l[0].isdigit() or l.startswith(prep_art) or l.startswith(preposizioni)):
        return f"{verbo} {l}"
    femminili = ("cucina", "sala", "borsa", "scatola", "camera", "tasca", "soffitta", "cantina", "mensola", "scrivania", "sedia")
    if l.startswith(femminili):
        return f"{verbo} nella {l}"
    if l.startswith(("scaffale", "tavolo", "divano", "letto", "comodino", "balcone", "terrazzo", "ripiano", "bracciolo")):
        return f"{verbo} sul {l}"
    if l.startswith(("cassetto", "armadio", "garage", "bagno", "salotto", "ufficio", "frigo", "forno", "macchina", "auto", "zaino", "portafoglio", "mobile", "disimpegno", "ingresso")):
        return f"{verbo} nel {l}"
    return f"{verbo} in {l}"

def tenta_separazione_intelligente(testo_intero):
    t = str(testo_intero).lower().strip()
    separatori = [" nello ", " nella ", " nell' ", " nell'", " nel ", " nei ", " negli ", " nelle ", " sullo ", " sulla ", " sulle ", " sull'", " sul ", " sopra ", " sotto ", " dietro ", " dentro ", " in ", " a ", " il ", " alle ", " per le ", " l'", " lo ", " tra ", " fra "]
    for s in separatori:
        if s in t:
            parti = t.split(s, 1)
            obj_clean = pulisci_testo(parti[0])
            if not obj_clean: return None, None
            return obj_clean, s.strip() + " " + parti[1].strip()
    return None, None

def genera_risposta_lista(handler_input, filtro=None, raw_input="", forza_report=False):
    f_v = str(filtro).lower() if filtro else ""
    r_v = str(raw_input).lower() if raw_input else ""

    parole_chiusura = ["annulla", "basta", "stai ferma", "niente", "stop", "esci"]
    if any(word in f_v for word in parole_chiusura) or any(word in r_v for word in parole_chiusura):
        handler_input.attributes_manager.session_attributes["context"] = "NORMAL"
        return handler_input.response_builder.speak("Operazione annullata. Altro?").ask("Cosa vuoi fare?").response

    db = get_memoria(handler_input.request_envelope.session.user.user_id)
    if not db: return handler_input.response_builder.speak("Tutto vuoto. Altro?").ask("Altro?").response

    session = handler_input.attributes_manager.session_attributes

    intent_name = handler_input.request_envelope.request.intent.name
    modalita_report = forza_report or (intent_name == "ReportOggettiIntent") or any(p in f_v or p in r_v for p in ["report", "dettagli", "completa", "pieno"])
    mostra_solo_importanti = (session.get("context") == "WIPE_WARNING") or ("imp" in f_v)

    oggetti_filtrati = []
    messaggio_intro = ""

    if mostra_solo_importanti:
        oggetti_filtrati = [k for k, v in db.items() if "|IMP" in v]
        messaggio_intro = "Gli oggetti importanti sono"
    elif f_v and f_v not in ["lista", "report", "tutto", "dettagli", "memoria", "none"]:
        radice_f = get_radice(f_v)
        for k, v in db.items():
            val_c = v.replace("|IMP", "").lower()
            if (f_v in k) or (radice_f in get_radice(k)) or (f_v in val_c):
                oggetti_filtrati.append(k)
        messaggio_intro = "Ho trovato"
    else:
        parole_ok = ["lista", "tutto", "memoria", "memorizzato", "salvato", "elenco", "report", "dettagli", "riepilogo", "oggetti"]
        if modalita_report or (intent_name == "ListaOggettiIntent") or any(p in f_v or p in r_v for p in parole_ok):
            oggetti_filtrati = list(db.keys())
            messaggio_intro = "Hai salvato"
        else:
            return handler_input.response_builder.speak("Scusa, non ho capito bene. Vuoi cercare un oggetto o sentire la lista?").ask("Cosa vuoi fare?").response

    if oggetti_filtrati:
        if modalita_report:
            elenco = '. '.join([f"{o} {formatta_risposta_luogo(calcola_grammatica(o)[0], db[o])}" for o in oggetti_filtrati])
        else:
            elenco = ', '.join(oggetti_filtrati)
        if session.get("context") == "WIPE_WARNING":
            return handler_input.response_builder.speak(f"{messaggio_intro}: {elenco}. Vuoi cancellarli comunque?").ask("Cancello?").response
        return handler_input.response_builder.speak(f"{messaggio_intro}: {elenco}. C'e altro?").ask("Altro?").response
    else:
        msg = "Non ho trovato oggetti importanti. Altro?" if mostra_solo_importanti else f"Non ho trovato nulla con '{f_v}'. Altro?"
        return handler_input.response_builder.speak(msg).ask("Altro?").response

# --- HANDLERS ---

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_request_type("LaunchRequest")(handler_input)
    def handle(self, handler_input):
        return handler_input.response_builder.speak("Ciao! Sono Trova Tutto. Cosa vuoi fare?").ask("Dimmi pure.").response

class SalvaOggettoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("SalvaOggettoIntent")(handler_input)
    def handle(self, handler_input):
        slots, session = handler_input.request_envelope.request.intent.slots, handler_input.attributes_manager.session_attributes
        input_obj = slots.get("oggetto").value if slots.get("oggetto") else None
        if input_obj and any(word in str(input_obj).lower() for word in ["annulla", "basta", "ferma"]):
            session["context"] = "NORMAL"
            return handler_input.response_builder.speak("Operazione annullata. Altro?").ask("Cosa vuoi fare?").response

        if session.get("context") != "CHECK_IMPORTANCE": session["context"] = "NORMAL"
        input_loc, mem_obj = slots.get("luogo").value if slots.get("luogo") else None, session.get("tmp_obj")
        final_obj, final_loc = input_obj, input_loc

        if final_obj and not final_loc:
            check_k = str(final_obj).lower().strip()
            if check_k in ["importante", "importanti", "tutto", "lista", "quali", "report", "dettagli"]:
                return genera_risposta_lista(handler_input, filtro=check_k, raw_input=check_k)

        if mem_obj and final_obj:
            pre = ("in ", "nel ", "nella ", "nell'", "nei ", "negli ", "nelle ", "su ", "sul ", "sulla ", "sull'", "sui ", "sugli ", "sulle ", "a ", "al ", "allo ", "alla ", "all'", "ai ", "agli ", "alle ", "da ", "dal ", "dalla ", "dall'", "dai ", "dagli ", "dalle ", "sotto ", "sopra ", "dietro ", "dentro ", "vicino ", "accanto ", "tra ", "fra ", "il ", "l'", "lo ", "domani", "dopodomani", "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica", "gennaio", "febbraio", "marzo")
            if final_obj.lower().startswith(pre) or (final_obj and final_obj[0].isdigit()):
                final_loc, final_obj = final_obj, mem_obj
            elif not final_loc:
                final_loc, final_obj = final_obj, mem_obj

        if not final_obj and final_loc and mem_obj: final_obj = mem_obj
        if final_obj and not final_loc:
            c_o, c_l = tenta_separazione_intelligente(final_obj)
            if c_o and c_l: final_obj, final_loc = c_o, c_l

        if not final_obj: return handler_input.response_builder.speak("Cosa vuoi salvare?").ask("Dimmi l'oggetto.").response
        obj_p = pulisci_testo(final_obj)
        if not final_loc:
            session["tmp_obj"] = final_obj
            return handler_input.response_builder.speak(f"Dove {calcola_grammatica(obj_p)[2]} metti?").ask("Dove?").response

        uid = handler_input.request_envelope.session.user.user_id
        db, msg_r = get_memoria(uid), "Ricevuto. E importante?"
        if obj_p in db:
            ex_l = db[obj_p].replace("|IMP", "")
            if ex_l.lower().strip() == final_loc.lower().strip():
                session.pop("tmp_obj", None)
                return handler_input.response_builder.speak(f"Ce l'ho gia cosi: {obj_p} {formatta_risposta_luogo('e', ex_l)}. Altro?").ask("Altro?").response
            c = 2
            while f"{obj_p} {c}" in db: c += 1
            obj_p = f"{obj_p} {c}"
            msg_r = f"Ok, aggiunto {obj_p}. E importante?"

        session["pending_save"] = {"obj": obj_p, "loc": final_loc}
        session["context"] = "CHECK_IMPORTANCE"
        session.pop("tmp_obj", None)
        return handler_input.response_builder.speak(msg_r).ask("E importante?").response

class CercaOggettoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("CercaOggettoIntent")(handler_input)
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        val = slots.get("oggetto").value if slots.get("oggetto") else None
        if val and any(word in str(val).lower() for word in ["annulla", "basta", "ferma"]):
            handler_input.attributes_manager.session_attributes["context"] = "NORMAL"
            return handler_input.response_builder.speak("Operazione annullata. Altro?").ask("Cosa vuoi fare?").response
        handler_input.attributes_manager.session_attributes.pop("tmp_obj", None)
        cercato = pulisci_testo(val)
        if not cercato: return handler_input.response_builder.speak("Cosa cerchiamo?").ask("Cosa?" ).response
        handler_input.attributes_manager.session_attributes["context"] = "NORMAL"
        db, ris = get_memoria(handler_input.request_envelope.session.user.user_id), []
        c_sup = pulisci_per_ricerca(cercato)
        for k, v_raw in db.items():
            v_c = v_raw.replace("|IMP", "").lower()
            m_key = (cercato in k) or (k in cercato) or (c_sup and c_sup in k) or (get_radice(c_sup) in get_radice(k))
            m_val = (cercato in v_c) or (c_sup and c_sup in v_c) or (get_radice(c_sup) in get_radice(v_c))
            if m_key or m_val: ris.append((k, f"{k} {formatta_risposta_luogo(calcola_grammatica(k)[0], v_raw)}"))
        if not ris: return handler_input.response_builder.speak(f"Non trovo nulla con '{cercato}'. Altro?").ask("Altro?").response
        if len(ris) == 1:
            handler_input.attributes_manager.session_attributes.update({"oggetto_in_sospeso": ris[0][0], "context": "DELETE_CONFIRMATION"})
            return handler_input.response_builder.speak(f"Ho trovato: {ris[0][1]}. Vuoi cancellarlo?").ask("Cancello?").response
        msg = f"Ho trovato {len(ris)} risultati: " + ", ".join([r[1] for r in ris]) + ". C'e altro?"
        return handler_input.response_builder.speak(msg).ask("Altro?").response

class CancellaOggettoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("CancellaOggettoIntent")(handler_input)
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        slot_obj = slots.get("oggetto") if slots else None
        raw_obj = slot_obj.value if (slot_obj and getattr(slot_obj, "value", None)) else ""
        da_c = pulisci_testo(raw_obj)
        if not da_c: return handler_input.response_builder.speak("Cosa vuoi cancellare?").ask("Cosa?" ).response
        uid = handler_input.request_envelope.session.user.user_id
        db, trovato = get_memoria(uid), None
        for k in db.keys():
            if da_c in k or k in da_c or get_radice(da_c) in get_radice(k):
                trovato = k; break
        if trovato:
            del db[trovato]; salva_memoria(uid, db)
            return handler_input.response_builder.speak(f"Ok, {trovato} rimosso. Altro?").ask("Altro?").response
        return handler_input.response_builder.speak(f"Non ho trovato {da_c}. Altro?").ask("Altro?").response

class ListaOggettiHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("ListaOggettiIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        slot_f = slots.get("filtro") if slots else None
        raw_v = slot_f.value if (slot_f and getattr(slot_f, "value", None)) else ""
        if session.get("tmp_obj") and not raw_v.strip():
            obj = pulisci_testo(session.get("tmp_obj"))
            pron = calcola_grammatica(obj)[2]
            return handler_input.response_builder.speak(
                f"Per farmi capire dove {pron} hai messo, dimmi per esempio: nel cassetto, sul mobile, oppure in borsa."
            ).ask("Dimmi: nel cassetto, sul mobile, oppure in borsa.").response
        session.pop("tmp_obj", None)
        return genera_risposta_lista(handler_input, filtro=pulisci_testo(raw_v), raw_input=raw_v)

class ReportOggettiHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("ReportOggettiIntent")(handler_input)
    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        raw_v = slots.get("filtro").value if slots.get("filtro") else ""
        return genera_risposta_lista(handler_input, filtro=pulisci_testo(raw_v), raw_input=raw_v, forza_report=True)

class SvuotaTuttoHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("SvuotaTuttoIntent")(handler_input)
    def handle(self, handler_input):
        uid = handler_input.request_envelope.session.user.user_id
        db = get_memoria(uid)
        if not db: return handler_input.response_builder.speak("Memoria gia vuota. Altro?").ask("Altro?").response
        imp = [k for k, v in db.items() if "|IMP" in v]
        if imp:
            handler_input.attributes_manager.session_attributes["context"] = "WIPE_WARNING"
            return handler_input.response_builder.speak(f"Attenzione! Ci sono {len(imp)} oggetti importanti. Vuoi cancellare anche quelli?").ask("Cancello anche quelli?").response
        handler_input.attributes_manager.session_attributes["context"] = "WIPE_FINAL_CHECK"
        return handler_input.response_builder.speak("Questa azione e irreversibile. Sei proprio sicura?").ask("Confermi?").response

class YesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.YesIntent")(handler_input)
    def handle(self, handler_input):
        s = handler_input.attributes_manager.session_attributes
        ctx, uid = s.get("context"), handler_input.request_envelope.session.user.user_id
        if ctx == "CHECK_IMPORTANCE":
            d = s.pop("pending_save", None)
            if d:
                db = get_memoria(uid); db[d["obj"]] = d["loc"] + "|IMP"; salva_memoria(uid, db)
                s["context"] = "NORMAL"
                return handler_input.response_builder.speak("Salvato come importante. Altro?").ask("Altro?").response
        if ctx == "DELETE_CONFIRMATION":
            obj = s.pop("oggetto_in_sospeso", None)
            db = get_memoria(uid)
            if obj and obj in db: del db[obj]; salva_memoria(uid, db)
            s["context"] = "NORMAL"
            return handler_input.response_builder.speak("Cancellato. Altro?").ask("Altro?").response
        if ctx == "WIPE_WARNING":
            s["context"] = "WIPE_FINAL_CHECK"
            return handler_input.response_builder.speak("Questa azione e irreversibile. Sei proprio sicura?").ask("Confermi definitivamente?").response
        if ctx == "WIPE_FINAL_CHECK" or ctx == "WIPE_CONFIRM_ALL":
            salva_memoria(uid, {}); s["context"] = "NORMAL"
            return handler_input.response_builder.speak("Ok, archivio svuotato. Altro?").ask("Altro?").response
        if ctx == "WIPE_CONFIRM_REST":
            db = get_memoria(uid); n_db = {k: v for k, v in db.items() if "|IMP" in v}
            salva_memoria(uid, n_db); s["context"] = "NORMAL"
            return handler_input.response_builder.speak("Fatto. Ho tenuto gli oggetti importanti e cancellato il resto. Altro?").ask("Altro?").response
        return genera_risposta_lista(handler_input)

class NoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.NoIntent")(handler_input)
    def handle(self, handler_input):
        s = handler_input.attributes_manager.session_attributes
        ctx, uid = s.get("context"), handler_input.request_envelope.session.user.user_id
        if ctx == "CHECK_IMPORTANCE":
            d = s.pop("pending_save", None)
            if d:
                db = get_memoria(uid); db[d["obj"]] = d["loc"];
                salva_memoria(uid, db)
                s["context"] = "NORMAL"
                return handler_input.response_builder.speak("Salvato. Altro?").ask("Altro?").response
        if ctx == "DELETE_CONFIRMATION":
            s.pop("oggetto_in_sospeso", None); s["context"] = "NORMAL"
            return handler_input.response_builder.speak("Ok, lo tengo. Altro?").ask("Altro?").response
        if ctx == "WIPE_WARNING":
            s["context"] = "WIPE_CONFIRM_REST"
            return handler_input.response_builder.speak("Ok, proteggo gli importanti. Questa azione e irreversibile. Sei proprio sicura?").ask("Cancello il resto?").response
        if ctx in ["WIPE_FINAL_CHECK", "WIPE_CONFIRM_ALL", "WIPE_CONFIRM_REST"]:
            s["context"] = "NORMAL"
            return handler_input.response_builder.speak("D'accordo, non ho toccato nulla. Altro?").ask("Altro?").response
        return handler_input.response_builder.speak("A presto!").set_should_end_session(True).response

class CancelIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.CancelIntent")(handler_input)
    def handle(self, handler_input):
        s = handler_input.attributes_manager.session_attributes
        s["context"] = "NORMAL"; s.pop("pending_save", None); s.pop("oggetto_in_sospeso", None); s.pop("tmp_obj", None)
        return handler_input.response_builder.speak("Operazione annullata. Cosa vuoi fare?").ask("Dimmi pure.").response

class StopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.StopIntent")(handler_input)
    def handle(self, handler_input):
        s = handler_input.attributes_manager.session_attributes
        # Uscita dal menu aiuto
        if s.get("context") == "HELP_MAIN":
            s.pop("context", None)
            return handler_input.response_builder.speak("D'accordo, torniamo a noi. Cosa vuoi fare?").ask("Cosa vuoi fare?").response
        return handler_input.response_builder.speak("A presto!").set_should_end_session(True).response

class AiutoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.HelpIntent")(handler_input)
                or is_intent_name("AiutoIntent")(handler_input))
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        argomento = None
        if slots and slots.get("argomento") and slots["argomento"].value:
            argomento = slots["argomento"].value.lower().strip()

        # CONTESTUALE: sta aspettando il luogo
        if session.get("tmp_obj"):
            oggetto = session.get("tmp_obj", "questo oggetto")
            obj_p = pulisci_testo(oggetto)
            pron = calcola_grammatica(obj_p)[2]
            return handler_input.response_builder.speak(
                f"Stai salvando {obj_p}. Dimmi dove {pron} metti, "
                "per esempio: nel cassetto, sul tavolo, oppure in borsa."
            ).ask("Dove lo metti?").response

        # SOTTOSEZIONE SALVARE
        if argomento and "salv" in argomento:
            session["context"] = "HELP_MAIN"
            return handler_input.response_builder.speak(
                "Per salvare di' per esempio: salva chiavi nel cassetto. "
                "Oppure in due tempi: salva chiavi, poi ti chiedo dove, e tu dici nel cassetto. "
                "Per una data di': salva visita medica il tre marzo. "
                "Vuoi sapere altro? Dimmi aiuto cercare, aiuto liste, oppure annulla per tornare."
            ).ask("Dimmi aiuto cercare, aiuto liste, oppure annulla.").response

        # SOTTOSEZIONE CERCARE
        if argomento and "cerc" in argomento:
            session["context"] = "HELP_MAIN"
            return handler_input.response_builder.speak(
                "Per cercare di': dove ho messo il telefono. "
                "Per un appuntamento di': cosa c'e a marzo. "
                "Puoi anche cercare per luogo dicendo: cosa c'e nel cassetto. "
                "Oppure cerca direttamente per nome dicendo: cerca visite, "
                "e ti mostro tutto quello che contiene quella parola. "
                "Vuoi sapere altro? Dimmi aiuto salvare, aiuto liste, oppure annulla per tornare."
            ).ask("Dimmi aiuto salvare, aiuto liste, oppure annulla.").response

        # SOTTOSEZIONE LISTE
        if argomento and ("list" in argomento or "report" in argomento):
            session["context"] = "HELP_MAIN"
            return handler_input.response_builder.speak(
                "Con lista senti solo i nomi. Con report senti anche dove si trova ogni cosa. "
                "Puoi filtrare entrambi dicendo per esempio: lista cassetto, oppure lista marzo. "
                "Lo stesso vale per report: prova a dire report visite, oppure report marzo, "
                "per sentire solo gli appuntamenti. "
                "Vuoi sapere altro? Dimmi aiuto salvare, aiuto cercare, oppure annulla per tornare."
            ).ask("Dimmi aiuto salvare, aiuto cercare, oppure annulla.").response

        # MENU PRINCIPALE
        session["context"] = "HELP_MAIN"
        return handler_input.response_builder.speak(
            "Su cosa vuoi aiuto? Puoi dirmi: aiuto salvare, aiuto cercare, oppure aiuto liste."
        ).ask("Dimmi aiuto salvare, aiuto cercare, oppure aiuto liste.").response

class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_intent_name("AMAZON.FallbackIntent")(handler_input)
    def handle(self, handler_input):
        session = handler_input.attributes_manager.session_attributes
        if session.get("tmp_obj"):
            obj = pulisci_testo(session.get("tmp_obj"))
            pron = calcola_grammatica(obj)[2]
            return handler_input.response_builder.speak(
                f"Per farmi capire dove {pron} hai messo, dimmi per esempio: nel cassetto, sul mobile, oppure in borsa."
            ).ask("Dimmi: nel cassetto, sul mobile, oppure in borsa.").response
        # Contestuale: menu aiuto
        if session.get("context") == "HELP_MAIN":
            return handler_input.response_builder.speak(
                "Non ho capito. Puoi dirmi: aiuto salvare, aiuto cercare, oppure aiuto liste. "
                "Oppure di' annulla per tornare."
            ).ask("Dimmi aiuto salvare, aiuto cercare, aiuto liste, oppure annulla.").response
        return handler_input.response_builder.speak(
            "Scusa, non ho capito. Puoi ripetere con calma?"
        ).ask("Ripeti.").response

class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input): return is_request_type("SessionEndedRequest")(handler_input)
    def handle(self, handler_input): return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception): return True
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        return handler_input.response_builder.speak("Scusa, non ho capito bene. Ripeti?").ask("Ripeti.").response

sb = CustomSkillBuilder()
sb.add_request_handler(LaunchRequestHandler()); sb.add_request_handler(SalvaOggettoHandler())
sb.add_request_handler(CercaOggettoHandler()); sb.add_request_handler(CancellaOggettoHandler())
sb.add_request_handler(ListaOggettiHandler()); sb.add_request_handler(ReportOggettiHandler())
sb.add_request_handler(SvuotaTuttoHandler()); sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler()); sb.add_request_handler(CancelIntentHandler())
sb.add_request_handler(StopIntentHandler()); sb.add_request_handler(AiutoIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler()); sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()