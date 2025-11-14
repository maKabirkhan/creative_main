from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.helpers.security import get_current_user
from app.helpers.db import supabase
from datetime import datetime, timedelta
import os
import stripe
from pydantic import BaseModel, field_validator


router = APIRouter()

class CheckoutRequest(BaseModel):
    plan: str
    
    @field_validator('plan')
    @classmethod
    def validate_plan(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Plan must be a non-empty string")
        return v.strip().lower()
    
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "professional": os.getenv("STRIPE_PRICE_PROFESSIONAL"),
    "agency": os.getenv("STRIPE_PRICE_AGENCY"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
}

PRICE_TO_TIER = {v: k for k, v in PRICE_IDS.items() if v}


@router.post("/")
def create_checkout_session(
    request: CheckoutRequest,
    user=Depends(get_current_user)
):
    """
    Create a Stripe Checkout session for a subscription.
    
    Request body (JSON):
    {
        "plan": "starter | professional | agency | enterprise"
    }
    """
    plan = request.plan
    
    if plan not in PRICE_IDS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid plan name: '{plan}'. Valid options are: {', '.join(PRICE_IDS.keys())}"
        )
    
    print("Stripe Mode:", "TEST" if "test" in stripe.api_key else "LIVE")

    price_id = PRICE_IDS[plan]
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Stripe price ID not set for plan: {plan}")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=user["email"],
            success_url="http://localhost:8080/upgrade",
            cancel_url="http://localhost:8080/cancel",
            metadata={
                "user_id": str(user["id"]),
                "plan": plan,
                "price_id": price_id
            },
        )

        return {
            "message": "Checkout session created successfully.",
            "plan": plan,
            "checkout_url": session.url,
            "session_id": session.id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/status")
def get_user_plan_status(user=Depends(get_current_user)):
    """
    Get the current user's active subscription plan.
    """
    user_id = user["id"]

    response = (
        supabase.table("subscriptions")
        .select("tier, start_date, end_date, auto_renew, status, stripe_subscription_id")
        .eq("user_id", user_id)
        .order("start_date", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return {
            "plan": "free",
            "message": "No active subscription found, defaulting to free plan."
        }

    sub = response.data[0]
    
    # Check if subscription is still active
    end_date = datetime.fromisoformat(sub["end_date"].replace("Z", ""))
    is_active = end_date > datetime.utcnow() and sub.get("status") == "active"

    return {
        "plan": sub["tier"] if is_active else "free",
        "start_date": sub.get("start_date"),
        "end_date": sub.get("end_date"),
        "auto_renew": sub.get("auto_renew"),
        "status": sub.get("status"),
        "is_active": is_active
    }


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events for subscription updates.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    print(f"\n{'='*80}")
    print(f"🔔 WEBHOOK RECEIVED AT {datetime.utcnow().isoformat()}")
    print(f"{'='*80}")
    print(f"📦 Payload length: {len(payload)}")
    print(f"🔑 Signature present: {bool(sig_header)}")
    print(f"🔐 Webhook secret configured: {bool(WEBHOOK_SECRET)}")

    try:
        if WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, WEBHOOK_SECRET
            )
        else:
            import json
            event = json.loads(payload)
            print("⚠️ WARNING: Webhook signature verification skipped (no secret)")
    except ValueError as e:
        print(f"❌ Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    print(f"📥 Received Stripe event: {event['type']}")
    print(f"📄 Event ID: {event.get('id', 'N/A')}")

    # Handle successful checkout
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_completed(session)

    # Handle subscription updates (plan changes, renewals)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        handle_subscription_updated(subscription)

    # Handle subscription deletion/cancellation
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        handle_subscription_deleted(subscription)

    # Handle failed payments
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        handle_payment_failed(invoice)

    return {"status": "success"}

from app.routers.project import reset_projects_count
def reset_pretests_count(user_id):
    """Reset the pretests counter for a user to 0"""
    try:
        result = supabase.table("users").update({
            "pretests_count": 0
        }).eq("id", user_id).execute()
        print(f"✅ Reset pretests_count to 0 for user {user_id}")
        return result
    except Exception as e:
        print(f"❌ Error resetting pretests_count: {str(e)}")
        raise


def handle_checkout_completed(session):
    """Process completed checkout session"""
    try:
        print(f"\n{'='*60}")
        print(f"💳 CHECKOUT COMPLETED")
        print(f"{'='*60}")
        
        customer_email = session.get("customer_email")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        
        metadata = session.get("metadata", {})
        plan = metadata.get("plan", "free")
        user_id = metadata.get("user_id")
        
        print(f"📧 Email: {customer_email}")
        print(f"👤 User ID: {user_id}")
        print(f"📦 Plan: {plan}")
        print(f"🔑 Customer ID: {customer_id}")
        print(f"🔑 Subscription ID: {subscription_id}")
        
        if not user_id:
            print(f"❌ ERROR: No user_id in metadata")
            print(f"   Available metadata: {metadata}")
            return
        
        if subscription_id:
            try:
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                print(f"🔍 Retrieved subscription object")
                print(f"   Subscription keys: {list(stripe_subscription.keys())[:10]}...")
                
                if hasattr(stripe_subscription, 'current_period_end'):
                    period_end_timestamp = stripe_subscription.current_period_end
                elif 'current_period_end' in stripe_subscription:
                    period_end_timestamp = stripe_subscription['current_period_end']
                else:
                    period_end_timestamp = None
                    
                if period_end_timestamp:
                    current_period_end = datetime.fromtimestamp(period_end_timestamp)
                    print(f"📅 Period ends: {current_period_end}")
                else:
                    current_period_end = datetime.utcnow() + timedelta(days=30)
                    print(f"⚠️ current_period_end not found in subscription, using default 30 days")
                    print(f"   Available fields: {list(stripe_subscription.keys())}")
            except Exception as sub_error:
                print(f"⚠️ Error retrieving subscription: {sub_error}")
                current_period_end = datetime.utcnow() + timedelta(days=30)
                print(f"⚠️ Using default 30 days")
        else:
            current_period_end = datetime.utcnow() + timedelta(days=30)
            print(f"⚠️ No subscription_id, using default 30 days")

        print(f"🔑 Using user_id: {user_id} (type: {type(user_id).__name__})")

        subscription_data = {
            "tier": plan,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": current_period_end.isoformat(),
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "auto_renew": True,
            "status": "active"
        }
        
        print(f"\n📝 Subscription data to save:")
        for key, value in subscription_data.items():
            print(f"   {key}: {value}")
        
        # Check if subscription exists
        print(f"\n🔍 Checking for existing subscription...")
        existing_sub = supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
        print(f"   Found {len(existing_sub.data)} existing subscription(s)")
        
        if existing_sub.data:
            # Update existing subscription
            print(f"\n🔄 Updating existing subscription...")
            result = supabase.table("subscriptions").update(subscription_data).eq("user_id", user_id).execute()
            print(f"✅ UPDATE SUCCESS")
            print(f"   Rows affected: {len(result.data)}")
            if result.data:
                print(f"   Updated record: {result.data[0]}")
        else:
            # Create new subscription
            print(f"\n➕ Creating new subscription...")
            subscription_data["user_id"] = user_id
            result = supabase.table("subscriptions").insert(subscription_data).execute()
            print(f"✅ INSERT SUCCESS")
            print(f"   Rows inserted: {len(result.data)}")
            if result.data:
                print(f"   New record: {result.data[0]}")
        
        # 🔄 RESET COUNTERS when user purchases a subscription
        if plan != "free":
            print(f"\n🔄 Resetting counters for paid plan: {plan}")
            try:
                reset_projects_count(user_id)
                print(f"✅ Project counter reset successfully")
            except Exception as reset_error:
                print(f"⚠️ Warning: Failed to reset project counter: {reset_error}")
            
            try:
                reset_pretests_count(user_id)
                print(f"✅ Pretest counter reset successfully")
            except Exception as reset_error:
                print(f"⚠️ Warning: Failed to reset pretest counter: {reset_error}")
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ERROR in handle_checkout_completed")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")


def handle_subscription_updated(subscription):
    """Process subscription updates (renewals, plan changes)"""
    try:
        print(f"\n{'='*60}")
        print(f"🔄 SUBSCRIPTION UPDATED")
        print(f"{'='*60}")
        
        subscription_id = subscription["id"]
        price_id = subscription["items"]["data"][0]["price"]["id"]
        current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
        status = subscription["status"]
        
        # Determine tier from price_id
        tier = PRICE_TO_TIER.get(price_id, "free")
        
        print(f"🔑 Subscription ID: {subscription_id}")
        print(f"💰 Price ID: {price_id}")
        print(f"📦 Tier: {tier}")
        print(f"📊 Status: {status}")
        print(f"📅 Period ends: {current_period_end}")
        
        # Get the old tier to check if it's an upgrade
        old_sub = supabase.table("subscriptions") \
            .select("tier, user_id") \
            .eq("stripe_subscription_id", subscription_id) \
            .execute()
        
        old_tier = None
        user_id = None
        if old_sub.data:
            old_tier = old_sub.data[0].get("tier")
            user_id = old_sub.data[0].get("user_id")
            print(f"📊 Old tier: {old_tier}")
            print(f"👤 User ID: {user_id}")
        
        # Update subscription by stripe_subscription_id
        update_data = {
            "tier": tier,
            "end_date": current_period_end.isoformat(),
            "status": status,
            "auto_renew": not subscription.get("cancel_at_period_end", False)
        }
        
        print(f"\n📝 Update data:")
        for key, value in update_data.items():
            print(f"   {key}: {value}")
        
        result = supabase.table("subscriptions").update(update_data).eq("stripe_subscription_id", subscription_id).execute()
        
        print(f"✅ UPDATE SUCCESS")
        print(f"   Rows affected: {len(result.data)}")
        if result.data:
            print(f"   Updated record: {result.data[0]}")
        
        # 🔄 RESET COUNTERS if plan upgraded (and not just a renewal)
        if user_id and tier != "free" and old_tier != tier:
            print(f"\n🔄 Plan changed from {old_tier} to {tier}, resetting counters")
            try:
                reset_projects_count(user_id)
                print(f"✅ Project counter reset successfully")
            except Exception as reset_error:
                print(f"⚠️ Warning: Failed to reset project counter: {reset_error}")
            
            try:
                reset_pretests_count(user_id)
                print(f"✅ Pretest counter reset successfully")
            except Exception as reset_error:
                print(f"⚠️ Warning: Failed to reset pretest counter: {reset_error}")
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ERROR in handle_subscription_updated")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")


def handle_subscription_deleted(subscription):
    """Process subscription cancellation"""
    try:
        print(f"\n{'='*60}")
        print(f"❌ SUBSCRIPTION DELETED")
        print(f"{'='*60}")
        
        subscription_id = subscription["id"]
        
        print(f"🔑 Subscription ID: {subscription_id}")
        
        # Update subscription to cancelled
        result = supabase.table("subscriptions").update({
            "tier": "free",
            "status": "cancelled",
            "auto_renew": False
        }).eq("stripe_subscription_id", subscription_id).execute()
        
        print(f"✅ CANCELLATION SUCCESS")
        print(f"   Rows affected: {len(result.data)}")
        if result.data:
            print(f"   Updated record: {result.data[0]}")
        
        print(f"ℹ️ Counters NOT reset - user falls back to free tier with existing counts")
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ERROR in handle_subscription_deleted")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")


def handle_payment_failed(invoice):
    """Process failed payment"""
    try:
        print(f"\n{'='*60}")
        print(f"⚠️ PAYMENT FAILED")
        print(f"{'='*60}")
        
        subscription_id = invoice.get("subscription")
        
        if subscription_id:
            print(f"🔑 Subscription ID: {subscription_id}")
            
            # Mark subscription as past_due
            result = supabase.table("subscriptions").update({
                "status": "past_due",
                "auto_renew": False
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            print(f"✅ MARKED AS PAST_DUE")
            print(f"   Rows affected: {len(result.data)}")
            if result.data:
                print(f"   Updated record: {result.data[0]}")
        else:
            print(f"⚠️ No subscription_id found in invoice")
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ERROR in handle_payment_failed")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")


@router.post("/cancel")
def cancel_subscription(user=Depends(get_current_user)):
    """
    Cancel user's subscription at the end of the current billing period.
    No refund - user keeps access until period ends.
    """
    try:
        user_id = user["id"]
        
        response = (
            supabase.table("subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        
        if not response.data:
            raise HTTPException(
                status_code=404, 
                detail="No active subscription found"
            )
        
        sub = response.data[0]
        stripe_subscription_id = sub.get("stripe_subscription_id")
        
        if not stripe_subscription_id:
            raise HTTPException(
                status_code=400, 
                detail="No Stripe subscription ID found"
            )
        
        stripe.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        supabase.table("subscriptions").update({
            "auto_renew": False
        }).eq("user_id", user_id).execute()
        
        return {
            "status": "success",
            "message": "Subscription will be cancelled at the end of the current billing period",
            "current_plan": sub["tier"],
            "access_until": sub["end_date"]
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))