"""Interfaces for the tau-bench retail benchmark.

Architecture:
  - tau_solve: top-level entry point; direct implementation manages the
    multi-turn conversation loop between retail_agent and user_simulator.
  - retail_agent: the customer service agent; simulate_pydantic with all
    retail tools injected, so it can call them during its reasoning loop.
  - user_simulator: plays the role of the customer; simulate or prompt_llm.
  - Retail tool stubs (16 tools): direct implementations delegating to the
    current environment's RetailTools instance.

Module-level state (_CURRENT_ENV, _TRANSFER_REQUESTED) is set at the start
of each tau_solve call and remains valid for the duration of that task.
"""

import json
from typing import List, Optional

from secretagent import config
from secretagent.core import interface

from tau_env import Order, Product, User, Variant, TauEnv, RetailTools

# ---------------------------------------------------------------
# Module-level environment state
# ---------------------------------------------------------------

_CURRENT_ENV: Optional[TauEnv] = None
_TRANSFER_REQUESTED: bool = False


def _reset_flags() -> None:
    global _TRANSFER_REQUESTED
    _TRANSFER_REQUESTED = False


def _tool_call(fn, *args, **kwargs) -> str:
    """Call a RetailTools method, returning error string on ValueError instead of raising.

    This prevents tool errors from propagating past pydantic-ai's retry limit,
    which would crash the entire tau_solve call. The agent sees the error string
    as the tool result and can adjust its approach.
    """
    try:
        result = fn(*args, **kwargs)
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json(indent=2)
        return str(result)
    except ValueError as e:
        return f"Error: {e}"


def load_env(env: TauEnv) -> None:
    """Set the environment to use for subsequent tau_solve calls."""
    global _CURRENT_ENV
    _CURRENT_ENV = env


# ---------------------------------------------------------------
# Retail tool interfaces (direct — delegate to _CURRENT_ENV.tools)
# ---------------------------------------------------------------

@interface
def calculate(expression: str) -> str:
    """Calculate the result of a mathematical expression.

    Args:
        expression: The expression to evaluate (numbers, +, -, *, /, parentheses).
    Returns:
        The numeric result as a string.
    """
    return _tool_call(_CURRENT_ENV.tools.calculate, expression)


@interface
def find_user_id_by_name_zip(first_name: str, last_name: str, zip: str) -> str:
    """Find user id by first name, last name, and zip code.

    Use this if the customer cannot provide their email address.
    Always authenticate via email first if available.

    Args:
        first_name: Customer's first name.
        last_name: Customer's last name.
        zip: Customer's zip code.
    Returns:
        The user id string, or an error message if not found.
    """
    return _tool_call(_CURRENT_ENV.tools.find_user_id_by_name_zip, first_name, last_name, zip)


@interface
def find_user_id_by_email(email: str) -> str:
    """Find user id by email address. Preferred authentication method.

    Args:
        email: Customer's email address.
    Returns:
        The user id string, or an error message if not found.
    """
    return _tool_call(_CURRENT_ENV.tools.find_user_id_by_email, email)


@interface
def get_order_details(order_id: str) -> str:
    """Get the status and details of an order.

    Args:
        order_id: The order id, e.g. '#W0000000'. Always include the '#' prefix.
    Returns:
        Order details as JSON, or an error message if not found.
    """
    return _tool_call(_CURRENT_ENV.tools.get_order_details, order_id)


@interface
def get_product_details(product_id: str) -> str:
    """Get the inventory details of a product type including all variants.

    Product id is different from item (variant) id.

    Args:
        product_id: The product type id.
    Returns:
        Product details as JSON, or an error message if not found.
    """
    return _tool_call(_CURRENT_ENV.tools.get_product_details, product_id)


@interface
def get_item_details(item_id: str) -> str:
    """Get the details of a specific item variant.

    Item id is different from product id.

    Args:
        item_id: The variant/item id.
    Returns:
        Variant details as JSON, or an error message if not found.
    """
    return _tool_call(_CURRENT_ENV.tools.get_item_details, item_id)


@interface
def get_user_details(user_id: str) -> str:
    """Get user profile including orders and payment methods.

    Args:
        user_id: The user id.
    Returns:
        User details as JSON, or an error message if not found.
    """
    return _tool_call(_CURRENT_ENV.tools.get_user_details, user_id)


@interface
def list_all_product_types() -> str:
    """List the name and product id of all 50 product types.

    Returns:
        JSON mapping product names to product ids.
    """
    return _tool_call(_CURRENT_ENV.tools.list_all_product_types)


@interface
def cancel_pending_order(order_id: str, reason: str) -> str:
    """Cancel a pending order and issue a refund.

    IMPORTANT: Explain details and get explicit 'yes' confirmation before calling.
    Gift card refunds are immediate; other methods take 5-7 business days.

    Args:
        order_id: The order id (include '#' prefix).
        reason: Either 'no longer needed' or 'ordered by mistake'.
    Returns:
        Updated order details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.cancel_pending_order, order_id, reason)


@interface
def modify_pending_order_address(
    order_id: str, address1: str, address2: str,
    city: str, state: str, country: str, zip: str,
) -> str:
    """Modify the shipping address of a pending order.

    IMPORTANT: Explain details and get explicit 'yes' confirmation before calling.

    Args:
        order_id: The order id (include '#' prefix).
        address1: Primary address line.
        address2: Secondary address line (use '' if none).
        city: City name.
        state: State abbreviation.
        country: Country name.
        zip: Postal code.
    Returns:
        Updated order details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.modify_pending_order_address,
                      order_id, address1, address2, city, state, country, zip)


@interface
def modify_pending_order_items(
    order_id: str, item_ids: List[str],
    new_item_ids: List[str], payment_method_id: str,
) -> str:
    """Swap items in a pending order. One-time only; changes status to 'pending (item modified)'.

    IMPORTANT: Confirm ALL items to change with customer before calling — this is irreversible.
    New items must be same product type but different variant.

    Args:
        order_id: The order id (include '#' prefix).
        item_ids: Current item ids to replace.
        new_item_ids: New item ids (same product, different variant).
        payment_method_id: Payment method for any price difference.
    Returns:
        Updated order details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.modify_pending_order_items,
                      order_id, item_ids, new_item_ids, payment_method_id)


@interface
def modify_pending_order_payment(order_id: str, payment_method_id: str) -> str:
    """Change the payment method for a pending order.

    IMPORTANT: Explain details and get explicit 'yes' confirmation before calling.

    Args:
        order_id: The order id (include '#' prefix).
        payment_method_id: New payment method id.
    Returns:
        Updated order details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.modify_pending_order_payment,
                      order_id, payment_method_id)


@interface
def modify_user_address(
    user_id: str, address1: str, address2: str,
    city: str, state: str, country: str, zip: str,
) -> str:
    """Update a user's default shipping address.

    IMPORTANT: Explain details and get explicit 'yes' confirmation before calling.

    Args:
        user_id: The user id.
        address1, address2, city, state, country, zip: New address fields.
    Returns:
        Updated user details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.modify_user_address,
                      user_id, address1, address2, city, state, country, zip)


@interface
def exchange_delivered_order_items(
    order_id: str, item_ids: List[str],
    new_item_ids: List[str], payment_method_id: str,
) -> str:
    """Exchange items in a delivered order. One-time only.

    IMPORTANT: Confirm ALL items to exchange before calling — irreversible.
    New items must be same product type but different variant.

    Args:
        order_id: The order id (include '#' prefix).
        item_ids: Item ids to exchange.
        new_item_ids: New item ids (same product, different variant).
        payment_method_id: Payment method for price difference.
    Returns:
        Updated order details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.exchange_delivered_order_items,
                      order_id, item_ids, new_item_ids, payment_method_id)


@interface
def return_delivered_order_items(
    order_id: str, item_ids: List[str], payment_method_id: str,
) -> str:
    """Return items from a delivered order.

    IMPORTANT: Explain details and get explicit 'yes' confirmation before calling.
    Refund goes to original payment method or a gift card.

    Args:
        order_id: The order id (include '#' prefix).
        item_ids: Item ids to return.
        payment_method_id: Payment method to receive refund.
    Returns:
        Updated order details as JSON, or an error message.
    """
    return _tool_call(_CURRENT_ENV.tools.return_delivered_order_items,
                      order_id, item_ids, payment_method_id)


@interface
def transfer_to_human_agents(summary: str) -> str:
    """Transfer the customer to a human agent.

    Use only when the request exceeds the agent's scope or the customer
    explicitly requests a human.

    Args:
        summary: Summary of the customer's issue.
    Returns:
        Transfer confirmation.
    """
    global _TRANSFER_REQUESTED
    _TRANSFER_REQUESTED = True
    return _tool_call(_CURRENT_ENV.tools.transfer_to_human_agents, summary)


# ---------------------------------------------------------------
# Agent interfaces
# ---------------------------------------------------------------

@interface
def retail_agent_ptp(conversation_str: str) -> str:
    """You are a retail customer service agent.

    The conversation_str shows the full conversation so far.
    Read it, pick the matching flow below, and execute it using the available tools.

    CANCEL a pending order:
    ```python
    user_id = find_user_id_by_email(email)          # or find_user_id_by_name_zip
    user    = get_user_details(user_id)
    order   = get_order_details(order_id)            # confirm status == 'pending'
    # present order details + reason, get explicit yes/no from customer
    result  = cancel_pending_order(order_id, reason) # reason: 'no longer needed' | 'ordered by mistake'
    return reply confirming cancellation and refund timeline
    ```

    EXCHANGE items in a delivered order:
    ```python
    user_id  = find_user_id_by_email(email)          # or find_user_id_by_name_zip
    user     = get_user_details(user_id)
    order    = get_order_details(order_id)            # confirm status == 'delivered'
    products = get_product_details(product_id)        # for each item, find available variants
    # collect ALL items to exchange before calling — this is one-time only
    # present details + price diff, get explicit yes/no from customer
    result   = exchange_delivered_order_items(order_id, item_ids, new_item_ids, payment_method_id)
    return reply confirming exchange and next steps
    ```

    RETURN items from a delivered order:
    ```python
    user_id = find_user_id_by_email(email)            # or find_user_id_by_name_zip
    user    = get_user_details(user_id)
    order   = get_order_details(order_id)             # confirm status == 'delivered'
    # present items + refund method, get explicit yes/no from customer
    result  = return_delivered_order_items(order_id, item_ids, payment_method_id)
    return reply confirming return and email instructions
    ```

    MODIFY a pending order (address / payment / items):
    ```python
    user_id = find_user_id_by_email(email)            # or find_user_id_by_name_zip
    user    = get_user_details(user_id)
    order   = get_order_details(order_id)             # confirm status == 'pending'
    # for item changes: get_product_details to find available variants first
    # present change details, get explicit yes/no from customer
    result  = modify_pending_order_address(...)       # or _payment / _items
    return reply confirming modification
    ```

    UPDATE user default address:
    ```python
    user_id = find_user_id_by_email(email)
    user    = get_user_details(user_id)
    # confirm new address with customer
    result  = modify_user_address(user_id, address1, address2, city, state, country, zip)
    return reply confirming update
    ```

    LOOK UP information (order status, product details, account info):
    ```python
    user_id = find_user_id_by_email(email)            # if account data needed
    data    = get_order_details(order_id)             # or get_product_details / get_user_details
    return reply with the requested information
    ```

    Rules that apply to ALL flows:
    - Always authenticate first (email preferred; fall back to name + zip)
    - Get explicit yes/no confirmation before any write action
    - One-time operations (exchange, modify items) — collect ALL changes before calling
    - Transfer to human agents only if request is out of scope

    Return ONLY your next agent response. Do not repeat the conversation.
    """


@interface
def retail_agent(conversation_str: str) -> str:
    """You are a customer service agent for an online retail store.

    The conversation_str shows the full conversation so far, formatted as:
      Customer: <message>
      Agent: <message>
      ...

    Your task: Generate your NEXT response as the agent. Use the available
    retail tools to look up information or make changes as needed.

    Policy:
    - Authenticate the customer first: use their email OR name + zip code
    - Serve only one customer per conversation
    - Before any write action, list all details and ask for explicit 'yes' confirmation
    - Only modify/cancel pending orders; only return/exchange delivered orders
    - Transfer to human agents only for out-of-scope requests
    - Do not make up information not obtained from tools

    Return ONLY your agent response (one turn). Do not repeat the conversation.
    """


@interface
def user_simulator(conversation_str: str, task_instructions: str) -> str:
    """Simulate a customer in a retail support conversation.

    You are roleplaying as a customer based on the task instructions.
    Respond naturally to the agent's last message.
    When the task has been completed satisfactorily, output [DONE] at the start.
    """


# ---------------------------------------------------------------
# Top-level interface
# ---------------------------------------------------------------

@interface
def tau_solve(task_id: str) -> str:
    """Solve a tau-bench retail task and return the reward.

    Runs the full multi-turn conversation between retail_agent and user_simulator.
    Returns the reward as a string: '1.0' (success) or '0.0' (failure).
    """
    _reset_flags()

    task = _CURRENT_ENV.get_task(task_id)
    initial_message = _CURRENT_ENV.reset(task_id)

    # Build task instructions string for user simulator
    inst = task.user_scenario.instructions if task.user_scenario else None
    task_instructions = _format_task_instructions(inst)

    # Conversation history as a simple list
    history: list[dict] = [{"role": "user", "content": initial_message}]

    max_turns = config.get("evaluate.max_turns", 15)

    for _turn in range(max_turns):
        # --- Agent turn ---
        conversation_str = _format_conversation(history)
        agent_response = retail_agent(conversation_str)
        history.append({"role": "assistant", "content": agent_response})

        # Check if agent transferred to human
        if _TRANSFER_REQUESTED or "transfer successful" in agent_response.lower():
            break

        # --- User turn ---
        user_response = user_simulator(conversation_str, task_instructions)
        history.append({"role": "user", "content": user_response})

        # Check if user signals task is complete
        if user_response.strip().upper().startswith("[DONE]"):
            break

    reward = _CURRENT_ENV.score()
    return str(reward)


# ---------------------------------------------------------------
# Workflow ptools: shared intent classifier
# ---------------------------------------------------------------

@interface
def classify_intent(conversation: str) -> str:
    """Classify the customer's current intent in a retail support conversation.

    Read the full conversation and identify what the customer is currently
    asking for. Return one of these labels:
      - "cancel_order" — customer wants to cancel a pending order
      - "exchange_items" — customer wants to exchange items in a delivered order
      - "return_items" — customer wants to return items from a delivered order
      - "modify_order" — customer wants to change address, payment, or items in a pending order
      - "modify_address" — customer wants to update their default shipping address
      - "lookup_info" — customer wants order status, product info, or account info
      - "other" — none of the above or unclear

    Return ONLY the label string, nothing else.
    """


# ---------------------------------------------------------------
# Workflow ptools: specialized plan_* agents (simulate_pydantic + restricted tools)
# ---------------------------------------------------------------

@interface
def plan_cancel(conversation: str) -> str:
    """You are a retail customer service agent handling an order cancellation request.

    The conversation_str shows the full conversation so far:
      Customer: <message>
      Agent: <message>
      ...

    Help the customer cancel their pending order. Steps:
    1. Authenticate via email or name + zip
    2. Look up the order to confirm it's pending
    3. Confirm details and cancellation reason with customer
    4. Cancel the order once customer confirms

    Use available tools. Return your NEXT agent response only.
    """


@interface
def plan_exchange(conversation: str) -> str:
    """You are a retail customer service agent handling an item exchange request.

    The conversation shows the full conversation so far.

    Help the customer exchange items in a delivered order for the same product
    with different options. Steps:
    1. Authenticate via email or name + zip
    2. Look up the order and products to find available variants
    3. Confirm all items to exchange and new items with customer
    4. Exchange once customer confirms (one-time action — collect all items first)

    Use available tools. Return your NEXT agent response only.
    """


@interface
def plan_return(conversation: str) -> str:
    """You are a retail customer service agent handling an item return request.

    The conversation shows the full conversation so far.

    Help the customer return items from a delivered order. Steps:
    1. Authenticate via email or name + zip
    2. Look up the order to confirm it's delivered
    3. Confirm which items to return and the refund payment method
    4. Process the return once customer confirms

    Use available tools. Return your NEXT agent response only.
    """


@interface
def plan_modify(conversation: str) -> str:
    """You are a retail customer service agent handling a pending order modification.

    The conversation shows the full conversation so far.

    Help the customer modify their pending order (address, payment, or items)
    or update their default shipping address. Steps:
    1. Authenticate via email or name + zip
    2. Look up the order or user details
    3. Confirm the modification details with customer
    4. Apply the change once customer confirms

    Note: item modification is one-time and irreversible — collect all changes first.
    Use available tools. Return your NEXT agent response only.
    """


@interface
def plan_lookup(conversation: str) -> str:
    """You are a retail customer service agent answering an information request.

    The conversation shows the full conversation so far.

    Help the customer look up order status, product information, or account details.
    1. Authenticate via email or name + zip if accessing account data
    2. Use tools to retrieve the requested information
    3. Present the information clearly

    Use available tools. Return your NEXT agent response only.
    """


@interface
def plan_generic(conversation: str) -> str:
    """You are a retail customer service agent.

    The conversation shows the full conversation so far. Handle this request
    using any available retail tools. Follow the store policy:
    - Authenticate before accessing account data
    - Confirm before any write action
    - Transfer to human agents if out of scope

    Use available tools. Return your NEXT agent response only.
    """


# ---------------------------------------------------------------
# Workflow ptools: structured_baseline (simulate only, no tools)
# ---------------------------------------------------------------

@interface
def plan_structured(conversation: str, intent: str) -> str:
    """Given a retail support conversation and the customer's intent,
    describe the ideal response plan without executing it.

    intent is one of: cancel_order, exchange_items, return_items,
    modify_order, modify_address, lookup_info, other.

    Think through: what information is needed, what action should be taken,
    what should the agent say next. Return a concise plan (2-4 sentences).
    """


@interface
def format_structured(plan: str, conversation: str) -> str:
    """Given a response plan and conversation history, generate the agent's
    next message to the customer.

    Write a natural, helpful customer service reply that follows the plan.
    Do not mention the plan itself. Return ONLY the agent's message.
    """


# ---------------------------------------------------------------
# Workflow entry points (plain Python — called via direct fn=)
# ---------------------------------------------------------------

def ptp_agent_turn(conversation: str) -> str:
    """PTP agent: one simulate_pydantic call per turn, multi-subflow trace in prompt."""
    return retail_agent_ptp(conversation)


def workflow_turn(conversation: str) -> str:
    """PTP-style workflow: classify intent → route to specialized plan ptool.

    Each plan_* ptool has the relevant subset of retail tools, keeping
    the agent focused on the current task type.
    """
    intent = classify_intent(conversation)
    intent_lower = intent.lower()

    if "cancel" in intent_lower:
        return plan_cancel(conversation)
    elif "exchange" in intent_lower or "swap" in intent_lower:
        return plan_exchange(conversation)
    elif "return" in intent_lower or "refund" in intent_lower:
        return plan_return(conversation)
    elif any(k in intent_lower for k in ["modify", "address", "payment", "change"]):
        return plan_modify(conversation)
    elif any(k in intent_lower for k in ["lookup", "info", "status", "check", "find"]):
        return plan_lookup(conversation)
    else:
        return plan_generic(conversation)


def structured_baseline_turn(conversation: str) -> str:
    """Rigid 3-step workflow: classify → plan → format. No tools.

    Baseline to show context isolation + lack of tool access degrades performance.
    """
    intent = classify_intent(conversation)
    plan = plan_structured(conversation, intent)
    return format_structured(plan, conversation)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _format_conversation(history: list[dict]) -> str:
    """Format conversation history as readable text."""
    lines = []
    for msg in history:
        role = "Customer" if msg["role"] == "user" else "Agent"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def _format_task_instructions(inst) -> str:
    """Format task instructions for the user simulator."""
    if inst is None:
        return "You are a customer who needs help with a retail order."
    parts = []
    if inst.task_instructions:
        parts.append(inst.task_instructions)
    if inst.reason_for_call:
        parts.append(f"Your request: {inst.reason_for_call}")
    if inst.known_info:
        parts.append(f"What you know: {inst.known_info}")
    if inst.unknown_info:
        parts.append(f"What you do NOT know: {inst.unknown_info}")
    return "\n".join(parts)
