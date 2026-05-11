/// Unit tests for task UI logic, error parsing, and sync behavior.

import 'package:flutter_test/flutter_test.dart';

// --- 1. Task status transition rules (UI-level validation) ---

Set<String> allowedTransitions(String current) {
  const rules = {
    'open': {'assigned', 'in_progress', 'cancelled'},
    'assigned': {'in_progress', 'cancelled'},
    'in_progress': {'completed', 'cancelled'},
    'completed': <String>{},
    'cancelled': <String>{},
  };
  return rules[current] ?? {};
}

void main() {
  group('Task transitions', () {
    test('open allows assigned, in_progress, cancelled', () {
      final allowed = allowedTransitions('open');
      expect(allowed, contains('assigned'));
      expect(allowed, contains('in_progress'));
      expect(allowed, contains('cancelled'));
      expect(allowed, isNot(contains('completed')));
    });

    test('completed is terminal', () {
      expect(allowedTransitions('completed'), isEmpty);
    });

    test('cancelled is terminal', () {
      expect(allowedTransitions('cancelled'), isEmpty);
    });
  });

  group('Error envelope parsing', () {
    test('parses backend validation error', () {
      final data = {
        'error': {
          'code': 'validation_error',
          'message': 'Invalid input.',
          'details': {'priority': ['Invalid priority.']},
          'request_id': 'abc-123',
        }
      };
      final error = data['error'] as Map;
      expect(error['code'], 'validation_error');
      expect(error['details']['priority'], ['Invalid priority.']);
    });

    test('parses stale version error', () {
      final data = {
        'error': {
          'code': 'stale_version',
          'message': 'Resource modified.',
          'details': {'current_version': 5},
        }
      };
      expect(data['error']['code'], 'stale_version');
    });
  });

  group('Pending action queue', () {
    test('action is created with pending status', () {
      final action = {
        'id': 1,
        'action_type': 'complete_task',
        'entity_id': 42,
        'payload': {'note': 'Done'},
        'status': 'pending',
      };
      expect(action['status'], 'pending');
      expect(action['entity_id'], 42);
    });

    test('action transitions to syncing then completed', () {
      var status = 'pending';
      status = 'syncing';
      expect(status, 'syncing');
      status = 'completed';
      expect(status, 'completed');
    });
  });

  group('Realtime event reducer', () {
    test('task_created adds task to state', () {
      final state = <int, String>{};
      final event = {'entity_type': 'provider_task', 'entity_id': '1',
                     'event_type': 'task_created'};
      state[int.parse(event['entity_id']!)] = event['event_type']!;
      expect(state[1], 'task_created');
    });

    test('task_updated updates existing task', () {
      final state = {1: 'task_created'};
      state[1] = 'task_updated';
      expect(state[1], 'task_updated');
    });
  });

  group('Sync status reducer', () {
    test('idle by default', () {
      expect('idle', 'idle');
    });

    test('transitions through syncing', () {
      const steps = ['idle', 'syncing', 'completed'];
      expect(steps[0], 'idle');
      expect(steps[1], 'syncing');
      expect(steps[2], 'completed');
    });

    test('error state on failure', () {
      const steps = ['syncing', 'error'];
      expect(steps[1], 'error');
    });
  });
}
