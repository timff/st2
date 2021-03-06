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

import six

from st2common.util import reference
import st2common.util.action_db as action_utils
from st2common.persistence.execution import ActionExecution
from st2common.persistence.action import RunnerType
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance, Rule
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common import log as logging


LOG = logging.getLogger(__name__)

SKIPPED = ['id', 'callback', 'action']


def _decompose_liveaction(liveaction_db):
    """
    Splits the liveaction into an ActionExecution compatible dict.
    """
    decomposed = {'liveaction': {}}
    liveaction_api = vars(LiveActionAPI.from_model(liveaction_db))
    for k in liveaction_api.keys():
        if k in SKIPPED:
            decomposed['liveaction'][k] = liveaction_api[k]
        else:
            decomposed[k] = getattr(liveaction_db, k)
    return decomposed


def create_execution_object(liveaction, publish=True):
    action_db = action_utils.get_action_by_ref(liveaction.action)
    runner = RunnerType.get_by_name(action_db.runner_type['name'])

    attrs = {
        'action': vars(ActionAPI.from_model(action_db)),
        'runner': vars(RunnerTypeAPI.from_model(runner))
    }
    attrs.update(_decompose_liveaction(liveaction))

    if 'rule' in liveaction.context:
        rule = reference.get_model_from_ref(Rule, liveaction.context.get('rule', {}))
        attrs['rule'] = vars(RuleAPI.from_model(rule))

    if 'trigger_instance' in liveaction.context:
        trigger_instance_id = liveaction.context.get('trigger_instance', {})
        trigger_instance_id = trigger_instance_id.get('id', None)
        trigger_instance = TriggerInstance.get_by_id(trigger_instance_id)
        trigger = reference.get_model_by_resource_ref(db_api=Trigger,
                                                      ref=trigger_instance.trigger)
        trigger_type = reference.get_model_by_resource_ref(db_api=TriggerType,
                                                           ref=trigger.type)
        trigger_instance = reference.get_model_from_ref(
            TriggerInstance, liveaction.context.get('trigger_instance', {}))
        attrs['trigger_instance'] = vars(TriggerInstanceAPI.from_model(trigger_instance))
        attrs['trigger'] = vars(TriggerAPI.from_model(trigger))
        attrs['trigger_type'] = vars(TriggerTypeAPI.from_model(trigger_type))

    parent = ActionExecution.get(liveaction__id=liveaction.context.get('parent', ''))
    if parent:
        attrs['parent'] = str(parent.id)

    execution = ActionExecutionDB(**attrs)
    execution = ActionExecution.add_or_update(execution, publish=publish)

    if parent:
        if str(execution.id) not in parent.children:
            parent.children.append(str(execution.id))
            ActionExecution.add_or_update(parent)

    return execution


def update_execution(liveaction_db, publish=True):
    execution = ActionExecution.get(liveaction__id=str(liveaction_db.id))
    decomposed = _decompose_liveaction(liveaction_db)
    for k, v in six.iteritems(decomposed):
        setattr(execution, k, v)
    execution = ActionExecution.add_or_update(execution, publish=publish)
    return execution


def get_descendants(actionexecution_id, descendant_depth=-1):
    """
    Returns all descendant executions upto the specified descendant_depth for
    the supplied actionexecution_id.
    """
    descendants = []
    current_level = set([actionexecution_id])
    next_level = set()
    remaining_depth = descendant_depth
    # keep track of processed ActionExecution to avoid any cycles. Will raise
    # an exception if a cycle is found.
    processed_action_executions = set()

    while current_level and remaining_depth != 0:
        parent_id = current_level.pop()
        processed_action_executions.add(parent_id)
        children = ActionExecution.query(parent=parent_id)
        LOG.debug('Found %s children for id %s.', len(children), parent_id)
        for child in children:
            if str(child.id) in processed_action_executions:
                raise Exception('child with id %s appeared multiple times.', str(child.id))
            if child.children:
                next_level.add(str(child.id))
        descendants.extend(children)
        # check if current_level is complete. If so start processing the next level.
        if not current_level:
            current_level.update(next_level)
            next_level.clear()
            remaining_depth = remaining_depth - 1

    return descendants
