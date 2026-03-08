# Trova Tutto

Skill Alexa in italiano per salvare e ritrovare oggetti con il luogo dove si trovano.
La memoria è persistente su DynamoDB per ogni utente.

## Struttura del progetto

```
trova-tutto-2/
├── lambda/                  # Codice Lambda (Node.js)
│   ├── index.js             # Handler principale con tutti gli intent
│   ├── index.test.js        # Test unitari (Jest)
│   └── package.json
├── skill-package/
│   ├── skill.json           # Manifest della skill
│   └── interactionModels/
│       └── custom/
│           └── it-IT.json   # Modello di interazione in italiano
├── ask-resources.json       # Configurazione ASK CLI
└── README.md
```

## Prerequisiti

- Node.js 18.x
- [ASK CLI](https://developer.amazon.com/en-US/docs/alexa/smapi/quick-start-alexa-skills-kit-command-line-interface.html)
- Account AWS con DynamoDB

## Installazione e deploy

```bash
cd lambda
npm install
cd ..
ask deploy
```

## Test unitari

```bash
cd lambda
npm install
npm test
```

---

## DOCUMENTAZIONE COMPLETA FUNZIONALE

### DESCRIZIONE GENERALE

La skill permette di:
- Salvare oggetti con il luogo dove si trovano.
- Cercare oggetti per nome o luogo.
- Visualizzare liste semplici (solo nomi).
- Visualizzare report dettagliati (nome + luogo).
- Cancellare singoli elementi.
- Svuotare tutta la memoria con protezione per gli importanti.
- Gestire un flag "Importante".

---

### 1) AVVIO SKILL

**Utente:** "Alexa, apri Trova Tutto"  
**Risposta:** "Ciao! Sono Trova Tutto. Cosa vuoi fare?"

---

### 2) SALVATAGGIO

#### A) Salvataggio in un colpo (oggetto + luogo)

Esempi:
- "Salva chiavi nel cassetto"
- "Metti telefono sul tavolo"
- "Segna documenti in borsa"
- "Ho infilato passaporto nello zaino"
- "Butta telecomando sul divano"

**Risposta:** "Ricevuto. È importante?"  
- "Sì" → salvato come importante  
- "No" → salvato normale

#### B) Salvataggio in due tempi

1. "Salva occhiali"
2. "Dove li metti?"
3. "Nel cassetto"
4. "Ricevuto. È importante?"
5. "No"
6. "Salvato. Altro?"

#### C) Oggetti duplicati

Se salvi lo stesso oggetto con luogo diverso: "chiavi" → poi "chiavi 2"

---

### 3) IMPORTANTE

Dopo il salvataggio:
- "Sì" → salva con flag importante
- "No" → salva normale

---

### 4) RICERCA

#### A) Ricerca per nome

- "Dove ho messo il telefono?"
- "Trova chiavi"
- "Cerca passaporto"
- "Non trovo gli occhiali"
- "Hai visto il telecomando?"

Se trova 1 risultato: "Ho trovato: telefono è sul tavolo. Vuoi cancellarlo?"  
Se trova più risultati: "Ho trovato 3 risultati: …"

#### B) Ricerca per luogo

- "Cosa c'è nel cassetto?"
- "Cosa c'è in borsa?"
- "Cosa c'è sul tavolo?"

#### C) Ricerca per data/parola chiave

- "Cosa c'è a marzo?"
- "Quando è la visita medica?"
- "Che impegni ho il tre marzo?"

---

### 5) CANCELLAZIONE DIRETTA

- "Cancella chiavi"
- "Elimina passaporto"
- "Togli telefono dalla memoria"
- "Dimentica occhiali"

---

### 6) CANCELLAZIONE GUIDATA

"Trova passaporto" → "Ho trovato: passaporto è nello zaino. Vuoi cancellarlo?"  
- "Sì" → cancella  
- "No" → mantiene

---

### 7) LISTE (solo nomi)

**Lista completa:**
- "Lista"
- "Elenco"
- "Dimmi cosa ho salvato"
- "Lista completa"

**Lista filtrata:**
- "Lista cassetto"
- "Elenco borsa"
- "Lista marzo"

**Lista importanti:**
- "Lista importanti"
- "Dimmi quelli importanti"

---

### 8) REPORT (nome + luogo)

**Report completo:**
- "Report"

Esempio risposta: "Hai salvato: chiavi sono nel cassetto. telefono è sul tavolo."

**Report filtrato:**
- "Report cassetto"
- "Report marzo"

**Report importanti:**
- "Report importanti"

---

### 9) SVUOTA TUTTO

- "Svuota tutto"
- "Cancella tutto"
- "Elimina tutto"
- "Resetta tutto"
- "Pulisci archivio"

Se esistono importanti: "Attenzione! Ci sono N oggetti importanti. Vuoi cancellare anche quelli?"  Dimmi quelli importanti
Se non esistono importanti: "Questa azione è irreversibile. Sei proprio sicura?"
----
Se esistono importanti: "Attenzione! Ci sono N oggetti importanti. Vuoi cancellare anche quelli?"
- "Dimmi quelli importanti"
- "Quali?"
Gli oggetti importanti sono: appuntamento mamma, passaporto. Vuoi cancellarli comunque?


### 10) ANNULLA / STOP

- "Annulla" → reset contesto
- "Basta" → chiusura skill

---

### 11) AIUTO

**Menu principale:** "Su cosa vuoi aiuto? Puoi dirmi: salvare, cercare, oppure liste."

- "Aiuto salvare" → esempi di salvataggio
- "Aiuto cercare" → esempi di ricerca
- "Aiuto liste" → differenza lista/report e filtri

