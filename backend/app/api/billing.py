"""
ClipForge AI — Billing (Stripe Checkout, one-time "Pro" purchase)

Flow: frontend calls POST /billing/checkout -> we create a Stripe Checkout
Session tagged with the user's id -> user pays on Stripe's hosted page ->
Stripe calls POST /billing/webhook -> we flip that user's plan to "pro".
The webhook (signature-verified) is the only thing that grants Pro.
"""

import asyncio
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout")
async def create_checkout(user: User = Depends(get_current_user)):
    settings = get_settings()
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(status_code=503, detail="Billing is not configured.")

    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        api_key=settings.stripe_secret_key,
        mode="payment",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        client_reference_id=user.id,
        customer_email=user.email,
        success_url=f"{settings.frontend_url}/?upgraded=1",
        cancel_url=f"{settings.frontend_url}/",
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload,
            request.headers.get("stripe-signature", ""),
            settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    if event["type"] == "checkout.session.completed":
        user_id = event["data"]["object"].get("client_reference_id")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.plan = "pro"
            await db.commit()
            logger.info(f"User {user.id} upgraded to pro")

    return {"received": True}
