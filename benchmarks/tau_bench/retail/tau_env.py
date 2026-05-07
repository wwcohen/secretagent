"""Retail environment for tau-bench.

Self-contained port of the tau2-bench retail domain:
  - Data models (Variant, Product, User, Order, RetailDB)
  - Tool implementations (RetailTools)
  - Task models (Task, UserScenario, EvaluationCriteria)
  - Environment wrapper (TauEnv)

No dependency on the tau2 package. Data files (db.json, tasks.json) are
downloaded separately via data/download.py.

Source: https://github.com/sierra-research/tau2-bench (MIT License)
"""

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------
# Data models (ported from tau2/domains/retail/data_model.py)
# ---------------------------------------------------------------

class Variant(BaseModel):
    """A specific variant of a product (e.g. blue, size L)."""
    item_id: str
    options: Dict[str, str]
    available: bool
    price: float


class Product(BaseModel):
    """A product type with its variants."""
    name: str
    product_id: str
    variants: Dict[str, Variant]


class UserName(BaseModel):
    first_name: str
    last_name: str


class UserAddress(BaseModel):
    address1: str
    address2: str
    city: str
    country: str
    state: str
    zip: str


class CreditCard(BaseModel):
    source: Literal["credit_card"]
    brand: str
    last_four: str
    id: str


class Paypal(BaseModel):
    source: Literal["paypal"]
    id: str


class GiftCard(BaseModel):
    source: Literal["gift_card"]
    balance: float
    id: str


PaymentMethod = Union[CreditCard, GiftCard, Paypal]


class User(BaseModel):
    user_id: str
    name: UserName
    address: UserAddress
    email: str
    payment_methods: Dict[str, PaymentMethod]
    orders: List[str]


class OrderFulfillment(BaseModel):
    tracking_id: List[str]
    item_ids: List[str]


class OrderItem(BaseModel):
    name: str
    product_id: str
    item_id: str
    price: float
    options: Dict[str, str]


OrderStatus = Literal[
    "processed",
    "pending",
    "pending (item modified)",
    "delivered",
    "cancelled",
    "exchange requested",
    "return requested",
]

CancelReason = Literal["no longer needed", "ordered by mistake"]


class OrderPayment(BaseModel):
    transaction_type: Literal["payment", "refund"]
    amount: float
    payment_method_id: str


class Order(BaseModel):
    order_id: str
    user_id: str
    address: UserAddress
    items: List[OrderItem]
    status: OrderStatus
    fulfillments: List[OrderFulfillment]
    payment_history: List[OrderPayment]
    cancel_reason: Optional[CancelReason] = None
    exchange_items: Optional[List[str]] = None
    exchange_new_items: Optional[List[str]] = None
    exchange_payment_method_id: Optional[str] = None
    exchange_price_difference: Optional[float] = None
    return_items: Optional[List[str]] = None
    return_payment_method_id: Optional[str] = None


class RetailDB(BaseModel):
    """The retail database: products, users, orders."""
    products: Dict[str, Product]
    users: Dict[str, User]
    orders: Dict[str, Order]

    @classmethod
    def from_json_file(cls, path: str | Path) -> "RetailDB":
        with open(path) as f:
            data = json.load(f)
        return cls.model_validate(data)

    def statistics(self) -> dict:
        return {
            "products": len(self.products),
            "users": len(self.users),
            "orders": len(self.orders),
            "variants": sum(len(p.variants) for p in self.products.values()),
        }


# ---------------------------------------------------------------
# Tool implementations (ported from tau2/domains/retail/tools.py)
# ---------------------------------------------------------------

class RetailTools:
    """All retail operations. Operates on a mutable RetailDB instance."""

    def __init__(self, db: RetailDB) -> None:
        self.db = db

    # --- private helpers ---

    def _get_order(self, order_id: str) -> Order:
        if order_id not in self.db.orders:
            raise ValueError("Order not found")
        return self.db.orders[order_id]

    def _get_user(self, user_id: str) -> User:
        if user_id not in self.db.users:
            raise ValueError("User not found")
        return self.db.users[user_id]

    def _get_product(self, product_id: str) -> Product:
        if product_id not in self.db.products:
            raise ValueError("Product not found")
        return self.db.products[product_id]

    def _get_item(self, item_id: str) -> Variant:
        for product in self.db.products.values():
            if item_id in product.variants:
                return product.variants[item_id]
        raise ValueError("Item not found")

    def _get_variant(self, product_id: str, variant_id: str) -> Variant:
        product = self._get_product(product_id)
        if variant_id not in product.variants:
            raise ValueError("Variant not found")
        return product.variants[variant_id]

    def _get_payment_method(self, user_id: str, payment_method_id: str) -> PaymentMethod:
        user = self._get_user(user_id)
        if payment_method_id not in user.payment_methods:
            raise ValueError("Payment method not found")
        return user.payment_methods[payment_method_id]

    def _is_pending_order(self, order: Order) -> bool:
        return "pending" in order.status

    # --- public tools ---

    def calculate(self, expression: str) -> str:
        """Calculate the result of a mathematical expression.

        Args:
            expression: Expression with numbers, operators (+,-,*,/), parens, and spaces.
        Returns:
            The numeric result as a string.
        """
        if not all(char in "0123456789+-*/(). " for char in expression):
            raise ValueError("Invalid characters in expression")
        return str(round(float(eval(expression, {"__builtins__": None}, {})), 2))

    def find_user_id_by_name_zip(self, first_name: str, last_name: str, zip: str) -> str:
        """Find user id by first name, last name, and zip code.

        Args:
            first_name: Customer's first name.
            last_name: Customer's last name.
            zip: Customer's zip code.
        Returns:
            The user id.
        Raises:
            ValueError: If the user is not found.
        """
        for user_id, user in self.db.users.items():
            if (
                user.name.first_name.lower() == first_name.lower()
                and user.name.last_name.lower() == last_name.lower()
                and user.address.zip == zip
            ):
                return user_id
        raise ValueError("User not found")

    def find_user_id_by_email(self, email: str) -> str:
        """Find user id by email address.

        Args:
            email: Customer's email address.
        Returns:
            The user id.
        Raises:
            ValueError: If the user is not found.
        """
        for user_id, user in self.db.users.items():
            if user.email.lower() == email.lower():
                return user_id
        raise ValueError("User not found")

    def get_order_details(self, order_id: str) -> Order:
        """Get the status and details of an order.

        Args:
            order_id: The order id, e.g. '#W0000000'. Include the '#' prefix.
        Returns:
            Full order details.
        """
        return self._get_order(order_id)

    def get_product_details(self, product_id: str) -> Product:
        """Get the inventory details of a product type.

        Args:
            product_id: The product id (not the item/variant id).
        Returns:
            Product with all variants.
        """
        return self._get_product(product_id)

    def get_item_details(self, item_id: str) -> Variant:
        """Get the inventory details of a specific item variant.

        Args:
            item_id: The item/variant id (not the product id).
        Returns:
            Variant details.
        """
        return self._get_item(item_id)

    def get_user_details(self, user_id: str) -> User:
        """Get user profile including orders and payment methods.

        Args:
            user_id: The user id.
        Returns:
            User details.
        """
        return self._get_user(user_id)

    def list_all_product_types(self) -> str:
        """List all 50 product types with their product ids.

        Returns:
            JSON string mapping product names to product IDs.
        """
        product_dict = {
            product.name: product.product_id
            for product in self.db.products.values()
        }
        return json.dumps(product_dict, sort_keys=True)

    def cancel_pending_order(self, order_id: str, reason: str) -> Order:
        """Cancel a pending order and process refund.

        The agent must explain details and get explicit user confirmation before calling this.
        Gift card refunds are immediate; other methods take 5-7 business days.

        Args:
            order_id: The order id (include '#' prefix).
            reason: Either 'no longer needed' or 'ordered by mistake'.
        Returns:
            Updated order details.
        Raises:
            ValueError: If order is not pending or reason is invalid.
        """
        order = self._get_order(order_id)
        if order.status != "pending":
            raise ValueError("Non-pending order cannot be cancelled")
        if reason not in {"no longer needed", "ordered by mistake"}:
            raise ValueError("Invalid reason")

        refunds = []
        for payment in order.payment_history:
            payment_id = payment.payment_method_id
            refund = OrderPayment(
                transaction_type="refund",
                amount=payment.amount,
                payment_method_id=payment_id,
            )
            refunds.append(refund)
            user = self._get_user(order.user_id)
            pm = self._get_payment_method(user.user_id, payment_id)
            if isinstance(pm, GiftCard):
                pm.balance += payment.amount
                pm.balance = round(pm.balance, 2)

        order.status = "cancelled"
        order.cancel_reason = reason
        order.payment_history.extend(refunds)
        return order

    def modify_pending_order_address(
        self, order_id: str, address1: str, address2: str,
        city: str, state: str, country: str, zip: str,
    ) -> Order:
        """Modify the shipping address of a pending order.

        Args:
            order_id: The order id (include '#' prefix).
            address1, address2, city, state, country, zip: New address fields.
        Returns:
            Updated order details.
        """
        order = self._get_order(order_id)
        if not self._is_pending_order(order):
            raise ValueError("Non-pending order cannot be modified")
        order.address = UserAddress(
            address1=address1, address2=address2,
            city=city, state=state, country=country, zip=zip,
        )
        return order

    def modify_pending_order_items(
        self, order_id: str, item_ids: List[str],
        new_item_ids: List[str], payment_method_id: str,
    ) -> Order:
        """Swap items in a pending order (same product type, different options). One-time only.

        Args:
            order_id: The order id (include '#' prefix).
            item_ids: Current item ids to replace.
            new_item_ids: New item ids (same product, different variant).
            payment_method_id: Payment method for price difference.
        Returns:
            Updated order details.
        """
        order = self._get_order(order_id)
        if order.status != "pending":
            raise ValueError("Non-pending order cannot be modified")

        all_item_ids = [item.item_id for item in order.items]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                raise ValueError(f"{item_id} not found")

        if len(item_ids) != len(new_item_ids):
            raise ValueError("The number of items to be exchanged should match")

        diff_price = 0
        variant = None
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            if item_id == new_item_id:
                raise ValueError("The new item id should be different from the old item id")
            item = next((i for i in order.items if i.item_id == item_id), None)
            if item is None:
                raise ValueError(f"Item {item_id} not found")
            variant = self._get_variant(item.product_id, new_item_id)
            if not variant.available:
                raise ValueError(f"New item {new_item_id} not found or available")
            diff_price += variant.price - item.price

        pm = self._get_payment_method(order.user_id, payment_method_id)
        if isinstance(pm, GiftCard) and pm.balance < diff_price:
            raise ValueError("Insufficient gift card balance")

        order.payment_history.append(
            OrderPayment(
                transaction_type="payment" if diff_price > 0 else "refund",
                amount=abs(diff_price),
                payment_method_id=payment_method_id,
            )
        )
        if isinstance(pm, GiftCard):
            pm.balance -= diff_price
            pm.balance = round(pm.balance, 2)

        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next((i for i in order.items if i.item_id == item_id), None)
            v = self._get_variant(item.product_id, new_item_id)
            item.item_id = new_item_id
            item.price = v.price
            item.options = v.options

        order.status = "pending (item modified)"
        return order

    def modify_pending_order_payment(self, order_id: str, payment_method_id: str) -> Order:
        """Change the payment method for a pending order.

        Args:
            order_id: The order id (include '#' prefix).
            payment_method_id: New payment method id.
        Returns:
            Updated order details.
        """
        order = self._get_order(order_id)
        if not self._is_pending_order(order):
            raise ValueError("Non-pending order cannot be modified")

        pm = self._get_payment_method(order.user_id, payment_method_id)

        if (
            len(order.payment_history) != 1
            or order.payment_history[0].transaction_type != "payment"
        ):
            raise ValueError("There should be exactly one payment for a pending order")

        if order.payment_history[0].payment_method_id == payment_method_id:
            raise ValueError("The new payment method should be different from the current one")

        amount = order.payment_history[0].amount
        if isinstance(pm, GiftCard) and pm.balance < amount:
            raise ValueError("Insufficient gift card balance")

        order.payment_history.extend([
            OrderPayment(transaction_type="payment", amount=amount,
                         payment_method_id=payment_method_id),
            OrderPayment(transaction_type="refund", amount=amount,
                         payment_method_id=order.payment_history[0].payment_method_id),
        ])

        if isinstance(pm, GiftCard):
            pm.balance -= amount
            pm.balance = round(pm.balance, 2)

        old_pm = self._get_payment_method(
            order.user_id, order.payment_history[0].payment_method_id)
        if isinstance(old_pm, GiftCard):
            old_pm.balance += amount
            old_pm.balance = round(old_pm.balance, 2)

        return order

    def modify_user_address(
        self, user_id: str, address1: str, address2: str,
        city: str, state: str, country: str, zip: str,
    ) -> User:
        """Update a user's default shipping address.

        Args:
            user_id: The user id.
            address1, address2, city, state, country, zip: New address fields.
        Returns:
            Updated user details.
        """
        user = self._get_user(user_id)
        user.address = UserAddress(
            address1=address1, address2=address2,
            city=city, state=state, country=country, zip=zip,
        )
        return user

    def exchange_delivered_order_items(
        self, order_id: str, item_ids: List[str],
        new_item_ids: List[str], payment_method_id: str,
    ) -> Order:
        """Exchange items in a delivered order for same product, different options. One-time only.

        Args:
            order_id: The order id (include '#' prefix).
            item_ids: Item ids to exchange.
            new_item_ids: New item ids (same product, different variant).
            payment_method_id: Payment method for price difference.
        Returns:
            Updated order details.
        """
        order = self._get_order(order_id)
        if order.status != "delivered":
            raise ValueError("Non-delivered order cannot be exchanged")

        all_item_ids = [item.item_id for item in order.items]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                raise ValueError(f"Number of {item_id} not found.")

        if len(item_ids) != len(new_item_ids):
            raise ValueError("The number of items to be exchanged should match.")

        diff_price = 0
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next((i for i in order.items if i.item_id == item_id), None)
            if item is None:
                raise ValueError(f"Item {item_id} not found")
            variant = self._get_variant(item.product_id, new_item_id)
            if not variant.available:
                raise ValueError(f"New item {new_item_id} not found or available")
            diff_price += variant.price - item.price

        diff_price = round(diff_price, 2)
        pm = self._get_payment_method(order.user_id, payment_method_id)
        if isinstance(pm, GiftCard) and pm.balance < diff_price:
            raise ValueError("Insufficient gift card balance to pay for the price difference")

        order.status = "exchange requested"
        order.exchange_items = sorted(item_ids)
        order.exchange_new_items = sorted(new_item_ids)
        order.exchange_payment_method_id = payment_method_id
        order.exchange_price_difference = diff_price
        return order

    def return_delivered_order_items(
        self, order_id: str, item_ids: List[str], payment_method_id: str,
    ) -> Order:
        """Return items from a delivered order.

        Refund goes to the original payment method or a gift card.

        Args:
            order_id: The order id (include '#' prefix).
            item_ids: Item ids to return.
            payment_method_id: Payment method to receive refund.
        Returns:
            Updated order details.
        """
        order = self._get_order(order_id)
        if order.status != "delivered":
            raise ValueError("Non-delivered order cannot be returned")

        user = self._get_user(order.user_id)
        pm = self._get_payment_method(user.user_id, payment_method_id)
        if (
            not isinstance(pm, GiftCard)
            and payment_method_id != order.payment_history[0].payment_method_id
        ):
            raise ValueError("Payment method should be the original payment method")

        all_item_ids = [item.item_id for item in order.items]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                raise ValueError("Some item not found")

        order.status = "return requested"
        order.return_items = sorted(item_ids)
        order.return_payment_method_id = payment_method_id
        return order

    def transfer_to_human_agents(self, summary: str) -> str:
        """Transfer the customer to a human agent.

        Use only when the request cannot be handled within the agent's scope,
        or when the customer explicitly requests a human agent.

        Args:
            summary: A summary of the customer's issue.
        Returns:
            Confirmation message.
        """
        return "Transfer successful"


# ---------------------------------------------------------------
# Task models (minimal subset of tau2's data_model/tasks.py)
# ---------------------------------------------------------------

class TaskInstructions(BaseModel):
    task_instructions: Optional[str] = None
    domain: Optional[str] = None
    reason_for_call: str = ""
    known_info: Optional[str] = None
    unknown_info: Optional[str] = None


class UserScenario(BaseModel):
    persona: Optional[str] = None
    instructions: Optional[TaskInstructions] = None


class EvaluationAction(BaseModel):
    action_id: str = ""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class EvaluationCriteria(BaseModel):
    actions: List[EvaluationAction] = Field(default_factory=list)
    communicate_info: List[Any] = Field(default_factory=list)
    nl_assertions: Optional[Any] = None
    reward_basis: List[str] = Field(default_factory=lambda: ["DB"])


class Task(BaseModel):
    id: str
    user_scenario: Optional[UserScenario] = None
    initial_state: Optional[Any] = None
    evaluation_criteria: Optional[EvaluationCriteria] = None
    description: Optional[Any] = None


# ---------------------------------------------------------------
# Environment wrapper
# ---------------------------------------------------------------

class TauEnv:
    """Manages state for a single tau-bench retail task.

    Usage:
        env = TauEnv(db_path, tasks_path)
        initial_msg = env.reset("task_42")
        # ... run conversation, retail tools modify env.tools.db ...
        reward = env.score()
    """

    def __init__(self, db_path: str | Path, tasks_path: str | Path) -> None:
        self._base_db = RetailDB.from_json_file(db_path)
        all_tasks_raw = json.loads(Path(tasks_path).read_text())
        self.tasks: dict[str, Task] = {
            t["id"]: Task.model_validate(t) for t in all_tasks_raw
        }
        self._current_task_id: Optional[str] = None
        self._initial_db: Optional[RetailDB] = None
        self.tools: Optional[RetailTools] = None

    def task_ids(self) -> list[str]:
        return list(self.tasks.keys())

    def get_task(self, task_id: str) -> Task:
        return self.tasks[task_id]

    def reset(self, task_id: str) -> str:
        """Reset the environment for a new task. Returns the initial user message."""
        self._current_task_id = task_id
        task = self.tasks[task_id]

        # Start from a fresh copy of the base DB
        self._initial_db = copy.deepcopy(self._base_db)
        self.tools = RetailTools(copy.deepcopy(self._initial_db))

        return self._get_initial_message(task)

    def _get_initial_message(self, task: Task) -> str:
        """Build the customer's opening message from task instructions."""
        if task.user_scenario is None or task.user_scenario.instructions is None:
            return "Hello, I need some help."
        inst = task.user_scenario.instructions
        parts = [inst.reason_for_call]
        if inst.known_info:
            parts.append(inst.known_info)
        return " ".join(p for p in parts if p)

    def score(self) -> float:
        """Score the current task by comparing final DB state to expected state.

        Applies all expected actions to a gold copy of the initial DB, then
        compares the gold state to the agent's final DB state.

        Returns:
            1.0 if DB state matches expected, 0.0 otherwise.
            Tasks with no evaluation criteria score 1.0 (trivially correct).

        Note: NL_ASSERTION-based scoring is not implemented (requires LLM judge).
        Only DB-based scoring is applied.
        """
        if self._current_task_id is None or self.tools is None:
            return 0.0

        task = self.tasks[self._current_task_id]

        if task.evaluation_criteria is None:
            return 1.0

        reward_basis = task.evaluation_criteria.reward_basis or ["DB"]

        if "DB" not in reward_basis:
            # No DB scoring required; we conservatively return 1.0
            # (NL_ASSERTION scoring would need an LLM judge)
            return 1.0

        # Build gold DB by applying expected actions to a fresh copy
        gold_db = copy.deepcopy(self._initial_db)
        gold_tools = RetailTools(gold_db)

        for action in task.evaluation_criteria.actions:
            fn = getattr(gold_tools, action.name, None)
            if fn is None:
                continue
            try:
                fn(**action.arguments)
            except Exception:
                pass  # best-effort; read-only tools safely no-op

        # Compare agent DB to gold DB
        agent_state = self.tools.db.model_dump()
        gold_state = gold_db.model_dump()

        return 1.0 if agent_state == gold_state else 0.0
