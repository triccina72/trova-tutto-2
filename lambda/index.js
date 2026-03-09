'use strict';

const Alexa = require('ask-sdk-core');
const { DynamoDbPersistenceAdapter } = require('ask-sdk-dynamodb-persistence-adapter');

// ---------------------------------------------------------------------------
// Persistence adapter
// ---------------------------------------------------------------------------
const persistenceAdapter = new DynamoDbPersistenceAdapter({
  tableName: process.env.DYNAMODB_TABLE || 'trova-tutto-users',
  createTable: true,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Load the items array from persistent storage. */
async function getItems(attributesManager) {
  const attrs = await attributesManager.getPersistentAttributes();
  return attrs.items || [];
}

/** Persist an updated items array. */
async function saveItems(attributesManager, items) {
  const attrs = await attributesManager.getPersistentAttributes();
  attrs.items = items;
  attributesManager.setPersistentAttributes(attrs);
  await attributesManager.savePersistentAttributes();
}

/**
 * Normalise a string for comparison: lowercase, trim, remove Italian articles
 * and elided preposition+article contractions (nell', sull', all', dall', l').
 */
function normalize(str) {
  if (!str) return '';
  return str
    .toLowerCase()
    .trim()
    .replace(/^(nell' ?|sull' ?|all' ?|dall' ?|l' ?|il |la |lo |i |le |gli |un |una |uno |dei |degli |delle |del |della |dello )/i, '')
    .trim();
}

/** Generate a unique item ID. */
function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/**
 * Given a base normalised name and the existing items, return how many items
 * share that base (e.g. "chiavi", "chiavi 2", "chiavi 3", …).
 */
function countDuplicates(base, items) {
  const escapedBase = base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`^${escapedBase}( \\d+)?$`);
  return items.filter(i => re.test(normalize(i.name))).length;
}

// ---------------------------------------------------------------------------
// Request handlers
// ---------------------------------------------------------------------------

const LaunchRequestHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak('Ciao! Sono Trova Tutto. Cosa vuoi fare?')
      .reprompt('Cosa vuoi fare?')
      .getResponse();
  },
};

// Save object + location in one shot ("salva chiavi nel cassetto")
const SalvaOggettoLuogoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'SalvaOggettoLuogoIntent'
    );
  },
  handle(handlerInput) {
    const oggetto = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Oggetto');
    const luogo = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Luogo');
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    sessionAttributes.state = 'WAITING_IMPORTANT';
    sessionAttributes.pendingItem = { name: oggetto, location: luogo };
    handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
    return handlerInput.responseBuilder
      .speak('Ricevuto. È importante?')
      .reprompt('È importante?')
      .getResponse();
  },
};

// Save object only – first step of two-step save ("salva chiavi")
const SalvaOggettoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'SalvaOggettoIntent'
    );
  },
  handle(handlerInput) {
    const oggetto = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Oggetto');
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    sessionAttributes.state = 'WAITING_LOCATION';
    sessionAttributes.pendingItem = { name: oggetto };
    handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
    return handlerInput.responseBuilder
      .speak('Dove vuoi metterlo?')
      .reprompt('Dove vuoi salvarlo?')
      .getResponse();
  },
};

// Receive location – second step of two-step save ("nel cassetto")
const InserisciLuogoIntentHandler = {
  canHandle(handlerInput) {
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'InserisciLuogoIntent' &&
      sessionAttributes.state === 'WAITING_LOCATION'
    );
  },
  handle(handlerInput) {
    const luogo = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Luogo');
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    sessionAttributes.pendingItem.location = luogo;
    sessionAttributes.state = 'WAITING_IMPORTANT';
    handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
    return handlerInput.responseBuilder
      .speak('Ricevuto. È importante?')
      .reprompt('È importante?')
      .getResponse();
  },
};

// Yes – used for: confirm important flag, confirm delete, confirm clear-all
const YesIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.YesIntent'
    );
  },
  async handle(handlerInput) {
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    const { state } = sessionAttributes;

    if (state === 'WAITING_IMPORTANT') {
      const items = await getItems(handlerInput.attributesManager);
      const base = normalize(sessionAttributes.pendingItem.name);
      const count = countDuplicates(base, items);
      const item = {
        id: generateId(),
        name: count > 0 ? `${sessionAttributes.pendingItem.name} ${count + 1}` : sessionAttributes.pendingItem.name,
        location: sessionAttributes.pendingItem.location,
        important: true,
        savedAt: new Date().toISOString(),
      };
      items.push(item);
      await saveItems(handlerInput.attributesManager, items);
      sessionAttributes.state = null;
      sessionAttributes.pendingItem = null;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak('Salvato come importante. Altro?')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    if (state === 'WAITING_DELETE_CONFIRM') {
      const itemId = sessionAttributes.pendingDelete;
      const items = await getItems(handlerInput.attributesManager);
      await saveItems(handlerInput.attributesManager, items.filter(i => i.id !== itemId));
      sessionAttributes.state = null;
      sessionAttributes.pendingDelete = null;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak('Cancellato. Altro?')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    if (state === 'WAITING_CLEAR_CONFIRM') {
      await saveItems(handlerInput.attributesManager, []);
      sessionAttributes.state = null;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak('Memoria svuotata. Altro?')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    return handlerInput.responseBuilder
      .speak('Non so cosa confermare. Cosa vuoi fare?')
      .reprompt('Cosa vuoi fare?')
      .getResponse();
  },
};

// No – used for: decline important flag, keep item, cancel clear-all
const NoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.NoIntent'
    );
  },
  async handle(handlerInput) {
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    const { state } = sessionAttributes;

    if (state === 'WAITING_IMPORTANT') {
      const items = await getItems(handlerInput.attributesManager);
      const base = normalize(sessionAttributes.pendingItem.name);
      const count = countDuplicates(base, items);
      const item = {
        id: generateId(),
        name: count > 0 ? `${sessionAttributes.pendingItem.name} ${count + 1}` : sessionAttributes.pendingItem.name,
        location: sessionAttributes.pendingItem.location,
        important: false,
        savedAt: new Date().toISOString(),
      };
      items.push(item);
      await saveItems(handlerInput.attributesManager, items);
      sessionAttributes.state = null;
      sessionAttributes.pendingItem = null;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak('Salvato. Altro?')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    if (state === 'WAITING_DELETE_CONFIRM') {
      sessionAttributes.state = null;
      sessionAttributes.pendingDelete = null;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak('Ok, mantenuto. Altro?')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    if (state === 'WAITING_CLEAR_CONFIRM') {
      sessionAttributes.state = null;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak('Ok, annullato. Altro?')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    return handlerInput.responseBuilder
      .speak('Ok. Cosa vuoi fare?')
      .reprompt('Cosa vuoi fare?')
      .getResponse();
  },
};

// Search by name ("dove ho messo il telefono", "trova chiavi")
const TrovaOggettoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'TrovaOggettoIntent'
    );
  },
  async handle(handlerInput) {
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    const oggetto = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Oggetto');
    const items = await getItems(handlerInput.attributesManager);
    const normalizedQuery = normalize(oggetto);
    const found = items.filter(i => normalize(i.name).includes(normalizedQuery));

    if (found.length === 0) {
      return handlerInput.responseBuilder
        .speak(`Non ho trovato nulla per ${oggetto}. Posso aiutarti con altro?`)
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    if (found.length === 1) {
      sessionAttributes.state = 'WAITING_DELETE_CONFIRM';
      sessionAttributes.pendingDelete = found[0].id;
      handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
      return handlerInput.responseBuilder
        .speak(`Ho trovato: ${found[0].name} è ${found[0].location}. Vuoi cancellarlo?`)
        .reprompt('Vuoi cancellarlo?')
        .getResponse();
    }

    const report = found.map(i => `${i.name} è ${i.location}`).join('. ');
    return handlerInput.responseBuilder
      .speak(`Ho trovato ${found.length} risultati: ${report}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Search by location or keyword ("cosa c'è nel cassetto", "cosa c'è a marzo")
const CosaHaiLuogoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'CosaHaiLuogoIntent'
    );
  },
  async handle(handlerInput) {
    const luogo = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Luogo');
    const items = await getItems(handlerInput.attributesManager);
    const normalizedQuery = normalize(luogo);
    const found = items.filter(
      i => normalize(i.location).includes(normalizedQuery) || normalize(i.name).includes(normalizedQuery),
    );

    if (found.length === 0) {
      return handlerInput.responseBuilder
        .speak(`Non ho trovato nulla per ${luogo}. Posso aiutarti con altro?`)
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    const names = found.map(i => i.name).join(', ');
    return handlerInput.responseBuilder
      .speak(`Per ${luogo} hai: ${names}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Direct delete ("cancella chiavi", "elimina passaporto")
const CancellaOggettoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'CancellaOggettoIntent'
    );
  },
  async handle(handlerInput) {
    const oggetto = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Oggetto');
    const items = await getItems(handlerInput.attributesManager);
    const normalizedQuery = normalize(oggetto);
    const found = items.filter(i => normalize(i.name).includes(normalizedQuery));

    if (found.length === 0) {
      return handlerInput.responseBuilder
        .speak(`Non ho trovato ${oggetto} in memoria. Posso aiutarti con altro?`)
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }

    const idsToDelete = new Set(found.map(i => i.id));
    await saveItems(handlerInput.attributesManager, items.filter(i => !idsToDelete.has(i.id)));
    const countMsg =
      found.length === 1 ? `${found[0].name} cancellato` : `Cancellati ${found.length} elementi`;
    return handlerInput.responseBuilder
      .speak(`${countMsg}. Altro?`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// List all – names only ("lista", "elenco", "cosa ho salvato")
const ListaIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'ListaIntent'
    );
  },
  async handle(handlerInput) {
    const items = await getItems(handlerInput.attributesManager);
    if (items.length === 0) {
      return handlerInput.responseBuilder
        .speak('Non hai salvato nulla.')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }
    const names = items.map(i => i.name).join(', ');
    return handlerInput.responseBuilder
      .speak(`Hai salvato: ${names}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Filtered list – names only ("lista cassetto", "elenco marzo")
const ListaFiltroIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'ListaFiltroIntent'
    );
  },
  async handle(handlerInput) {
    const filtro = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Filtro');
    const items = await getItems(handlerInput.attributesManager);
    const normalizedQuery = normalize(filtro);
    const found = items.filter(
      i => normalize(i.name).includes(normalizedQuery) || normalize(i.location).includes(normalizedQuery),
    );
    if (found.length === 0) {
      return handlerInput.responseBuilder
        .speak(`Nessun elemento trovato per ${filtro}.`)
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }
    const names = found.map(i => i.name).join(', ');
    return handlerInput.responseBuilder
      .speak(`Per ${filtro}: ${names}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Important list – names only ("importanti", "lista importanti")
const ListaImportantiIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'ListaImportantiIntent'
    );
  },
  async handle(handlerInput) {
    const items = await getItems(handlerInput.attributesManager);
    const importanti = items.filter(i => i.important);
    if (importanti.length === 0) {
      return handlerInput.responseBuilder
        .speak('Non hai salvato nessun elemento importante.')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }
    const names = importanti.map(i => i.name).join(', ');
    return handlerInput.responseBuilder
      .speak(`Gli importanti sono: ${names}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Full report – name + location ("report")
const ReportIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'ReportIntent'
    );
  },
  async handle(handlerInput) {
    const items = await getItems(handlerInput.attributesManager);
    if (items.length === 0) {
      return handlerInput.responseBuilder
        .speak('Non hai salvato nulla.')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }
    const report = items.map(i => `${i.name} è ${i.location}`).join('. ');
    return handlerInput.responseBuilder
      .speak(`Hai salvato: ${report}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Filtered report – name + location ("report cassetto", "report marzo")
const ReportFiltroIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'ReportFiltroIntent'
    );
  },
  async handle(handlerInput) {
    const filtro = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Filtro');
    const items = await getItems(handlerInput.attributesManager);
    const normalizedQuery = normalize(filtro);
    const found = items.filter(
      i => normalize(i.name).includes(normalizedQuery) || normalize(i.location).includes(normalizedQuery),
    );
    if (found.length === 0) {
      return handlerInput.responseBuilder
        .speak(`Nessun elemento trovato per ${filtro}.`)
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }
    const report = found.map(i => `${i.name} è ${i.location}`).join('. ');
    return handlerInput.responseBuilder
      .speak(`Per ${filtro}: ${report}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Important report – name + location ("report importanti")
const ReportImportantiIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'ReportImportantiIntent'
    );
  },
  async handle(handlerInput) {
    const items = await getItems(handlerInput.attributesManager);
    const importanti = items.filter(i => i.important);
    if (importanti.length === 0) {
      return handlerInput.responseBuilder
        .speak('Non hai salvato nessun elemento importante.')
        .reprompt('Posso aiutarti con altro?')
        .getResponse();
    }
    const report = importanti.map(i => `${i.name} è ${i.location}`).join('. ');
    return handlerInput.responseBuilder
      .speak(`Gli importanti: ${report}.`)
      .reprompt('Posso aiutarti con altro?')
      .getResponse();
  },
};

// Clear all ("svuota tutto", "cancella tutto") – with protection for importants
const SvuotaTuttoIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'SvuotaTuttoIntent'
    );
  },
  async handle(handlerInput) {
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    const items = await getItems(handlerInput.attributesManager);
    const importanti = items.filter(i => i.important);
    sessionAttributes.state = 'WAITING_CLEAR_CONFIRM';
    handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
    if (importanti.length > 0) {
      return handlerInput.responseBuilder
        .speak(
          `Attenzione! Ci sono ${importanti.length} oggetti importanti. Vuoi cancellare anche quelli?`,
        )
        .reprompt('Vuoi cancellare anche quelli importanti?')
        .getResponse();
    }
    return handlerInput.responseBuilder
      .speak('Questa azione è irreversibile. Sei proprio sicuro?')
      .reprompt('Sei sicuro?')
      .getResponse();
  },
};

// Help – main menu ("aiuto")
const HelpIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.HelpIntent'
    );
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak('Su cosa vuoi aiuto? Puoi dirmi: salvare, cercare, oppure liste.')
      .reprompt('Su cosa vuoi aiuto? Salvare, cercare, o liste?')
      .getResponse();
  },
};

// Help – save ("aiuto salvare")
const AiutoSalvareIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AiutoSalvareIntent'
    );
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak(
        'Per salvare puoi dire: salva chiavi nel cassetto. ' +
          'Oppure prima dici salva chiavi e poi ti chiedo dove. ' +
          'Puoi anche dire: salva visita medica il tre marzo.',
      )
      .reprompt('Come posso aiutarti?')
      .getResponse();
  },
};

// Help – search ("aiuto cercare")
const AiutoCercareIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AiutoCercareIntent'
    );
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak(
        "Per cercare puoi dire: dove ho messo il telefono, " +
          "oppure cosa c'è nel cassetto, oppure cerca visite.",
      )
      .reprompt('Come posso aiutarti?')
      .getResponse();
  },
};

// Help – lists/reports ("aiuto liste")
const AiutoListeIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AiutoListeIntent'
    );
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak(
        'Lista mostra solo i nomi. Report mostra nome e luogo. ' +
          'Puoi filtrare: lista cassetto, oppure report marzo.',
      )
      .reprompt('Come posso aiutarti?')
      .getResponse();
  },
};

// Cancel – reset context ("annulla")
const CancelIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.CancelIntent'
    );
  },
  handle(handlerInput) {
    const sessionAttributes = handlerInput.attributesManager.getSessionAttributes();
    sessionAttributes.state = null;
    sessionAttributes.pendingItem = null;
    sessionAttributes.pendingDelete = null;
    handlerInput.attributesManager.setSessionAttributes(sessionAttributes);
    return handlerInput.responseBuilder
      .speak('Ok, annullato. Cosa vuoi fare?')
      .reprompt('Cosa vuoi fare?')
      .getResponse();
  },
};

// Stop – close skill ("basta", "esci")
const StopIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StopIntent'
    );
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder.speak('A presto!').getResponse();
  },
};

// Fallback – unrecognised utterances
const FallbackIntentHandler = {
  canHandle(handlerInput) {
    return (
      Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest' &&
      Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.FallbackIntent'
    );
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak('Non ho capito. Puoi dire: salva, trova, lista, report, o aiuto.')
      .reprompt('Cosa vuoi fare?')
      .getResponse();
  },
};

// Session ended – required by Alexa
const SessionEndedRequestHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'SessionEndedRequest';
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder.getResponse();
  },
};

// Global error handler
const ErrorHandler = {
  canHandle() {
    return true;
  },
  handle(handlerInput, error) {
    console.error('Skill error:', error.message);
    return handlerInput.responseBuilder
      .speak('Scusa, si è verificato un errore. Riprova.')
      .reprompt('Riprova.')
      .getResponse();
  },
};

// ---------------------------------------------------------------------------
// Export Lambda handler
// ---------------------------------------------------------------------------
exports.handler = Alexa.SkillBuilders.custom()
  .withPersistenceAdapter(persistenceAdapter)
  .addRequestHandlers(
    LaunchRequestHandler,
    SalvaOggettoLuogoIntentHandler,
    SalvaOggettoIntentHandler,
    InserisciLuogoIntentHandler,
    YesIntentHandler,
    NoIntentHandler,
    TrovaOggettoIntentHandler,
    CosaHaiLuogoIntentHandler,
    CancellaOggettoIntentHandler,
    ListaImportantiIntentHandler,
    ListaFiltroIntentHandler,
    ListaIntentHandler,
    ReportImportantiIntentHandler,
    ReportFiltroIntentHandler,
    ReportIntentHandler,
    SvuotaTuttoIntentHandler,
    AiutoSalvareIntentHandler,
    AiutoCercareIntentHandler,
    AiutoListeIntentHandler,
    HelpIntentHandler,
    CancelIntentHandler,
    StopIntentHandler,
    FallbackIntentHandler,
    SessionEndedRequestHandler,
  )
  .addErrorHandlers(ErrorHandler)
  .lambda();

// Export helpers for unit testing
exports._normalize = normalize;
exports._countDuplicates = countDuplicates;
exports._generateId = generateId;
