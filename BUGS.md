# BUGS - Elenco problemi conosciuti e comportamenti indesiderati (Skill Trova Tutto)

## Bug 1: Falsi positivi sull'intento "Lista"
- **Problema:** Se l'utente apre la skill e pronuncia una parola singola casuale e non prevista (es. "casa"), Alexa attiva erroneamente il comando `ListaIntent` invece di rispondere con "Scusa, non ho capito". Di fatto viene interpretato come richiesta della lista oggetti anche per parole che non c'entrano nulla, dando una sensazione poco professionale.
- **Possibile soluzione:** Rivedere il modello di interazione nel file `it-IT.json` per ridurre i casi di collisione e rafforzare l'Intents Fallback.

## Bug 2: Parole con articolo attivano "SvuotaTuttoIntent"
- **Problema:** Pronunciando una parola preceduta da articolo (es. "La casa") Alexa attiva involontariamente l'intent di svuotamento totale della memoria (`SvuotaTuttoIntent`). Per fortuna c'è doppia conferma, ma è un comportamento rischioso.
- **Possibile soluzione:** Analizzare nel modello di interazione se la slot "Filtro" o "Lista" accetta valori troppo generici; aggiungere controlli lato codice per evitare attivazioni accidentali su parole inattese.

## Bug 3: Loop e blocco del menu Aiuto
- **Problema:** Quando si entra in "Aiuto" ("salvare", "cercare", "lista", ecc.) la skill non torna più al funzionamento normale dopo "Annulla", e spesso "Basta" chiude la skill in modo brusco. Dopo aver consultato la guida, le parole chiave restano agganciate alla guida e non alle relative funzionalità. L'unica soluzione attuale per l'utente è riavviare la skill.
- **Possibile soluzione:** Controllare che il valore di `session["context"]` venga sempre reimpostato a `NORMAL` sia nello `StopIntentHandler` che nel `CancelIntentHandler`. Rafforzare la gestione dell'uscita dal menu Aiuto sganciando correttamente le variabili di sessione.