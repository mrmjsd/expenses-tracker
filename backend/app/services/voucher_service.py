from app.models.voucher import Voucher,Item,Employee
from app.schemas.voucher import VoucherCreate, VoucherUpdate, VoucherRead 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.services.employee_service import EmployeeService
from app.services.payment_service import PaymentService
from app.services.vendor_details_service import VendorDetailsService
from app.services.financial_reporting_service import FinancialReportingService
from app.services.supply_performance_service import SupplyPerformanceService
from app.services.audit_trail_service import AuditTrailService

import logging
logger = logging.getLogger(__name__)

class VoucherService:
    def __init__(self, db: AsyncSession):
        self.db:AsyncSession = db
        self.employee_service = EmployeeService(db)
        self.payment_service = PaymentService(db)
        self.vendor_details_service = VendorDetailsService(db)
        self.financial_reporting_service = FinancialReportingService(db)
        self.supply_performance_service = SupplyPerformanceService(db)
        self.audit_trail_service = AuditTrailService(db)

    async def create_voucher(self, voucher_data: VoucherCreate):
        try:
            logger.info(f"Creating voucher: {voucher_data.dict()}")
            new_voucher = Voucher(**voucher_data.dict())
            self.db.add(new_voucher)
            await self.db.commit()
            await self.db.refresh(new_voucher)
            logger.info(f"Voucher created with ID: {new_voucher.id}")
            return new_voucher
        except Exception as e:
            logger.error(f"Error creating voucher: {e}")
            raise

    async def get_voucher(self, voucher_id: int):
        try:
            logger.info(f"Retrieving voucher with ID: {voucher_id}")
            result = await self.db.execute(select(Voucher).where(Voucher.id == voucher_id))
            voucher = result.scalar_one_or_none()
            if voucher:
                logger.info(f"Voucher retrieved with ID: {voucher_id}")
            else:
                logger.warning(f"Voucher with ID {voucher_id} not found")
            return voucher
        except Exception as e:
            logger.error(f"Error retrieving voucher with ID {voucher_id}: {e}")
            raise

    async def get_all_vouchers(self):
        try:
            logger.info("Retrieving all vouchers")
            result = await self.db.execute(select(Voucher))
            vouchers = result.scalars().all()
            logger.info(f"Retrieved {len(vouchers)} vouchers")
            return [VoucherRead.model_validate(voucher) for voucher in vouchers]
        except Exception as e:
            logger.error(f"Error retrieving all vouchers: {e}")
            raise

    async def update_voucher(self, voucher_id: int, voucher_update: VoucherUpdate):
        try:
            db_voucher = await self.get_voucher(voucher_id)
            if not db_voucher:
                logger.warning(f"Voucher with ID {voucher_id} not found for update")
                return None
            for key, value in voucher_update.dict(exclude_unset=True).items():
                setattr(db_voucher, key, value)
            await self.db.commit()
            logger.info(f"Voucher with ID {voucher_id} updated")
            return db_voucher
        except Exception as e:
            logger.error(f"Error updating voucher with ID {voucher_id}: {e}")
            raise

    async def delete_voucher(self, voucher_id: int):
        try:
            db_voucher = await self.get_voucher(voucher_id)
            if db_voucher:
                await self.db.delete(db_voucher)
                await self.db.commit()
                logger.info(f"Voucher with ID {voucher_id} deleted")
                return db_voucher
            else:
                logger.warning(f"Voucher with ID {voucher_id} not found for deletion")
                return None
        except Exception as e:
            logger.error(f"Error deleting voucher with ID {voucher_id}: {e}")
            raise

    async def create_voucher_from_json(self, voucher_data):
        try:
            # Extract voucher information
            voucher = voucher_data.get("voucher")
            voucher_to = voucher.get("voucher_to")
            vendor_details_data = voucher.get('vendor_details', {})
            financial_reporting_data = voucher.get('financial_reporting', {})
            supply_performance_data = voucher.get('supply_performance', {})
            audit_trail_data = voucher.get('audit_trail', {})

            # Create or get the employee
            employee_id = await self.employee_service.create_employee_if_not_exists(voucher_to)

            # Prepare the payment details
            payment_data = voucher.get("payment", {})
            payment_id = None

            # Create Payment if method is provided
            payment_method = payment_data.get("method")
            if payment_method:
                payment = await self.payment_service.create_payment(payment_data)
                payment_id = payment.id

            # Create VendorDetails entry
            vendor_details = await self.vendor_details_service.create_vendor_details(vendor_details_data)

            # Create FinancialReporting entry
            financial_reporting = await self.financial_reporting_service.create_financial_reporting(financial_reporting_data)

            # Create SupplyPerformance entry
            supply_performance = await self.supply_performance_service.create_supply_performance(supply_performance_data)

            # Create AuditTrail entry
            audit_trail = await self.audit_trail_service.create_audit_trail(audit_trail_data)

            # Create the Voucher
            new_voucher = Voucher(
                date=voucher.get("date"),
                voucher_no=voucher.get("voucher_no"),  # Handle this based on your earlier discussion
                prepared_by=voucher.get("prepared_by"),
                approved_by=voucher.get("approved_by"),
                authorized_by=voucher.get("authorized_by"),
                receiver_signature=voucher.get("receiver_signature"),
                employee_id=employee_id,
                payment_id=payment_id,
                total_amount=voucher.get("total_amount"),
                in_words=voucher.get("in_words"),
                expense_category=voucher.get("expense_category"),
                payment_status=voucher.get("payment_status"),
                payment_dues=voucher.get("payment_dues"),
                cash_flow_impact=voucher.get("cash_flow_impact"),
                vendor_details_id=vendor_details.id,
                financial_reporting_id=financial_reporting.id,
                supply_performance_id=supply_performance.id,
                audit_trail_id=audit_trail.id
            )

            self.db.add(new_voucher)
            await self.db.commit()
            await self.db.refresh(new_voucher)  # Refresh to get the ID
            # Add Items
            items_data = voucher.get("items", [])
            for item_data in items_data:
                item = Item(
                    description=item_data.get("description"),
                    amount=item_data.get("amount"),
                    voucher_id=new_voucher.id  # Associate the item with the new voucher
                )
                self.db.add(item)

            # Commit all items after adding
            await self.db.commit()

            logger.info(f"Voucher created with ID: {new_voucher.id}")
            return new_voucher

        except Exception as e:
            logger.error(f"Error creating voucher from JSON: {e}")
            raise
