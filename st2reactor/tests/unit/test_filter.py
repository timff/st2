# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import bson
import copy
import datetime
import mock
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, \
    RuleDB, ActionExecutionSpecDB
from st2common.models.db.action import ActionDB
from st2common.util import reference
from st2reactor.rules.filter import RuleFilter
from st2tests import DbTestCase


MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = bson.ObjectId()
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.pack = 'dummy_pack_1'
MOCK_TRIGGER.type = 'system.test'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = bson.ObjectId()
MOCK_TRIGGER_INSTANCE.trigger = MOCK_TRIGGER.get_reference().ref
MOCK_TRIGGER_INSTANCE.payload = {'p1': 'v1', 'bool': True, 'int': 1, 'float': 0.8}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.utcnow()

MOCK_ACTION = ActionDB()
MOCK_ACTION.id = bson.ObjectId()
MOCK_ACTION.name = 'action-test-1.name'

MOCK_RULE_1 = RuleDB()
MOCK_RULE_1.id = bson.ObjectId()
MOCK_RULE_1.name = "some1"
MOCK_RULE_1.trigger = reference.get_str_resource_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_1.criteria = {}
MOCK_RULE_1.action = ActionExecutionSpecDB(ref="somepack.someaction")

MOCK_RULE_2 = RuleDB()
MOCK_RULE_2.id = bson.ObjectId()
MOCK_RULE_1.name = "some2"
MOCK_RULE_2.trigger = reference.get_str_resource_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_2.criteria = {}
MOCK_RULE_2.action = ActionExecutionSpecDB(ref="somepack.someaction")


@mock.patch.object(reference, 'get_model_by_resource_ref',
                   mock.MagicMock(return_value=MOCK_TRIGGER))
class FilterTest(DbTestCase):
    def test_empty_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have failed.')

    def test_empty_payload(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v1'}}
        trigger_instance = copy.deepcopy(MOCK_TRIGGER_INSTANCE)
        trigger_instance.payload = None
        f = RuleFilter(trigger_instance, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'equals check should have failed.')

    def test_empty_criteria_and_empty_payload(self):
        rule = MOCK_RULE_1
        rule.criteria = {}
        trigger_instance = copy.deepcopy(MOCK_TRIGGER_INSTANCE)
        trigger_instance.payload = None
        f = RuleFilter(trigger_instance, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have failed.')

    def test_matchregex_operator_pass_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'matchregex', 'pattern': 'v1$'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'Failed to pass evaluation.')

    def test_matchregex_operator_fail_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'matchregex', 'pattern': 'v$'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'regex check should have failed.')

    def test_equals_operator_pass_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v1'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'regex check should have failed.')

    def test_equals_operator_fail_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'equals check should have failed.')

    def test_equals_bool_value(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.bool': {'type': 'equals', 'pattern': True}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have passed.')

    def test_equals_int_value(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.int': {'type': 'equals', 'pattern': 1}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have passed.')

    def test_equals_float_value(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.float': {'type': 'equals', 'pattern': 0.8}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have passed.')
