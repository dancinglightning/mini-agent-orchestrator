import asyncio
import random


async def cancel_order(order_id: str) -> dict:
    """Simulate cancelling an order. 20% chance of failure."""
    await asyncio.sleep(0.5)
    if random.random() < 0.2:
        return {"success": False, "order_id": order_id, "error": "Order cancellation failed: order is already shipped"}
    return {"success": True, "order_id": order_id, "message": f"Order {order_id} has been cancelled successfully"}


async def send_email(email: str, message: str) -> dict:
    """Simulate sending an email. Always succeeds after a 1-second delay."""
    await asyncio.sleep(1)
    return {"success": True, "email": email, "message": f"Email sent to {email}"}


TOOL_REGISTRY = {
    "cancel_order": cancel_order,
    "send_email": send_email,
}
