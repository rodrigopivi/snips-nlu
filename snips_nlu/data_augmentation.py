from __future__ import unicode_literals

from builtins import next
from copy import deepcopy
from itertools import cycle

from future.utils import iteritems

from snips_nlu.builtin_entities import is_builtin_entity
from snips_nlu.constants import (UTTERANCES, DATA, ENTITY, TEXT, INTENTS,
                                 ENTITIES, CAPITALIZE)
from snips_nlu.languages import get_default_sep
from snips_nlu.resources import get_stop_words
from snips_nlu.tokenization import tokenize_light


def capitalize(text, language):
    tokens = tokenize_light(text, language)
    stop_words = get_stop_words(language)
    return get_default_sep(language).join(
        t.title() if t.lower() not in stop_words
        else t.lower() for t in tokens)


def capitalize_utterances(utterances, entities, language, ratio, random_state):
    capitalized_utterances = []
    for utterance in utterances:
        capitalized_utterance = deepcopy(utterance)
        for i, chunk in enumerate(capitalized_utterance[DATA]):
            capitalized_utterance[DATA][i][TEXT] = chunk[TEXT].lower()
            if ENTITY not in chunk:
                continue
            entity_label = chunk[ENTITY]
            if is_builtin_entity(entity_label):
                continue
            if not entities[entity_label][CAPITALIZE]:
                continue
            if random_state.rand() > ratio:
                continue
            capitalized_utterance[DATA][i][TEXT] = capitalize(
                chunk[TEXT], language)
        capitalized_utterances.append(capitalized_utterance)
    return capitalized_utterances


def generate_utterance(contexts_iterator, entities_iterators):
    context = deepcopy(next(contexts_iterator))
    context_data = []
    for chunk in context[DATA]:
        if ENTITY in chunk:
            if not is_builtin_entity(chunk[ENTITY]):
                new_chunk = dict(chunk)
                new_chunk[TEXT] = deepcopy(
                    next(entities_iterators[new_chunk[ENTITY]]))
                context_data.append(new_chunk)
            else:
                context_data.append(chunk)
        else:
            context_data.append(chunk)
    context[DATA] = context_data
    return context


def get_contexts_iterator(dataset, intent_name, random_state):
    shuffled_utterances = random_state.permutation(
        dataset[INTENTS][intent_name][UTTERANCES])
    return cycle(shuffled_utterances)


def get_entities_iterators(intent_entities, random_state):
    entities_its = dict()
    for entity_name, entity in iteritems(intent_entities):
        shuffled_values = random_state.permutation(
            list(entity[UTTERANCES]))
        entities_its[entity_name] = cycle(shuffled_values)
    return entities_its


def get_intent_entities(dataset, intent_name):
    intent_entities = set()
    for utterance in dataset[INTENTS][intent_name][UTTERANCES]:
        for chunk in utterance[DATA]:
            if ENTITY in chunk:
                intent_entities.add(chunk[ENTITY])
    return intent_entities


def num_queries_to_generate(dataset, intent_name, min_utterances):
    nb_utterances = len(dataset[INTENTS][intent_name][UTTERANCES])
    return max(nb_utterances, min_utterances)


def augment_utterances(dataset, intent_name, language, min_utterances,
                       capitalization_ratio, random_state):
    contexts_it = get_contexts_iterator(dataset, intent_name, random_state)
    intent_entities = get_intent_entities(dataset, intent_name)
    intent_entities = {
        e: dataset[ENTITIES][e] for e in intent_entities
        if not is_builtin_entity(e)
    }
    entities_its = get_entities_iterators(intent_entities, random_state)
    generated_utterances = []
    nb_to_generate = num_queries_to_generate(dataset, intent_name,
                                             min_utterances)
    while nb_to_generate > 0:
        generated_utterance = generate_utterance(contexts_it, entities_its)
        generated_utterances.append(generated_utterance)
        nb_to_generate -= 1

    generated_utterances = capitalize_utterances(
        generated_utterances, dataset[ENTITIES], language,
        ratio=capitalization_ratio, random_state=random_state)

    return generated_utterances
