from sqlalchemy.orm import Session
from app.models.shift import Shift
from app.models.shift_expense import ShiftExpense
from app.schemas.shift import ShiftCreate
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import pytz
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.sql import label

class ShiftRepository:
    model = Shift
    
    def create(self, db: Session, shift: ShiftCreate, doctor_id: int) -> Shift:
        shift_data = vars(shift)

        shift_data['doctor_id'] = doctor_id
        shift_data['status'] = "scheduled"
        
        db_shift = Shift(**shift_data)
        db.add(db_shift)
        db.commit()
        db.refresh(db_shift)
        return db_shift
        
    def create_multiple_shifts(self, db: Session, shift_data: dict, doctor_id: int) -> list:
        result_shifts = []
        
        if shift_data.get('week_days') and isinstance(shift_data['week_days'], list):
            for day in shift_data['week_days']:
                single_shift_data = shift_data.copy()
                
                try:
                    from datetime import datetime
                    single_shift_data['date'] = datetime.strptime(day, '%Y-%m-%d').date()
                except ValueError:
                    continue
                
                del single_shift_data['week_days']
                if 'end_date' in single_shift_data:
                    del single_shift_data['end_date']
                
                shift = ShiftCreate(**single_shift_data)
                db_shift = self.create(db, shift, doctor_id)
                result_shifts.append(db_shift)
                
            return result_shifts
        else:
            shift = ShiftCreate(**shift_data)
            db_shift = self.create(db, shift, doctor_id)
            return [db_shift]

    def get_by_doctor(self, db: Session, doctor_id: int):
        return (
            db.query(Shift)
            .options(joinedload(Shift.hospital), joinedload(Shift.expenses))
            .filter(Shift.doctor_id == doctor_id)
            .all()
        )

    def get_by_id(self, db: Session, shift_id: int) -> Shift:
        return (
            db.query(Shift)
            .options(joinedload(Shift.expenses), joinedload(Shift.hospital))
            .filter(Shift.id == shift_id)
            .first()
        )

    def _sum_expenses_for_month(self, db: Session, doctor_id: int, year: int, month: int) -> float:
        total = (
            db.query(func.coalesce(func.sum(ShiftExpense.amount), 0))
            .filter(
                ShiftExpense.doctor_id == doctor_id,
                extract("month", ShiftExpense.expense_date) == month,
                extract("year", ShiftExpense.expense_date) == year,
            )
            .scalar()
        )
        return float(total)
    
    def get_dashboard_stats(self, db: Session, doctor_id: int) -> dict:
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        now = datetime.now(brazil_tz)
        current_month = now.month
        current_year = now.year
        # Mês anterior
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year

        monthly_earnings = db.query(
            func.coalesce(func.sum(Shift.value), 0).label("monthly_earnings")
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.payment_date) == current_month,
            extract('year', Shift.payment_date) == current_year,
            Shift.status.in_(["scheduled", "completed", "paid"]),
            Shift.payment_date.isnot(None)
        ).scalar()

        previous_month_earnings = db.query(
            func.coalesce(func.sum(Shift.value), 0).label("previous_month_earnings")
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.payment_date) == prev_month,
            extract('year', Shift.payment_date) == prev_year,
            Shift.status.in_(["scheduled", "completed", "paid"]),
            Shift.payment_date.isnot(None)
        ).scalar()

        expenses_total = self._sum_expenses_for_month(
            db, doctor_id, current_year, current_month
        )
        previous_expenses_total = self._sum_expenses_for_month(
            db, doctor_id, prev_year, prev_month
        )
        monthly_earnings_f = float(monthly_earnings)
        previous_month_earnings_f = float(previous_month_earnings)

        scheduled_shifts = db.query(
            func.count(Shift.id).label("scheduled_shifts")
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.date) == current_month,
            extract('year', Shift.date) == current_year,
            Shift.status.in_(["scheduled", "completed", "paid"])
        ).scalar()

        previous_scheduled_shifts = db.query(
            func.count(Shift.id).label("previous_scheduled_shifts")
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.date) == prev_month,
            extract('year', Shift.date) == prev_year,
            Shift.status.in_(["scheduled", "completed", "paid"])
        ).scalar()

        hours_worked = 0
        for shift in db.query(Shift).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.date) == current_month,
            extract('year', Shift.date) == current_year,
            Shift.status.in_(["scheduled", "completed", "paid"])
        ).all():
            start_seconds = shift.start_time.hour * 3600 + shift.start_time.minute * 60 + shift.start_time.second
            end_seconds = shift.end_time.hour * 3600 + shift.end_time.minute * 60 + shift.end_time.second
            if end_seconds < start_seconds:
                end_seconds += 24 * 3600
            hours = (end_seconds - start_seconds) / 3600
            if hours > 0:
                hours_worked += hours

        previous_hours_worked = 0
        for shift in db.query(Shift).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.date) == prev_month,
            extract('year', Shift.date) == prev_year,
            Shift.status.in_(["scheduled", "completed", "paid"])
        ).all():
            start_seconds = shift.start_time.hour * 3600 + shift.start_time.minute * 60 + shift.start_time.second
            end_seconds = shift.end_time.hour * 3600 + shift.end_time.minute * 60 + shift.end_time.second
            if end_seconds < start_seconds:
                end_seconds += 24 * 3600
            hours = (end_seconds - start_seconds) / 3600
            if hours > 0:
                previous_hours_worked += hours

        three_months_ago = (now - timedelta(days=90)).date()
        shifts = db.query(Shift).filter(
            Shift.doctor_id == doctor_id,
            Shift.date >= three_months_ago,
            Shift.date <= now.date(),
            Shift.status.in_(["scheduled", "paid", "completed"])
        ).all()
        total_value = 0
        total_hours = 0
        for shift in shifts:
            start_seconds = shift.start_time.hour * 3600 + shift.start_time.minute * 60 + shift.start_time.second
            end_seconds = shift.end_time.hour * 3600 + shift.end_time.minute * 60 + shift.end_time.second
            if end_seconds < start_seconds:
                end_seconds += 24 * 3600
            hours = (end_seconds - start_seconds) / 3600
            if hours > 0:
                total_value += float(shift.value)
                total_hours += hours
        avg_hourly_rate = total_value / total_hours if total_hours > 0 else 0

        # Média do mês anterior
        prev_shifts = db.query(Shift).filter(
            Shift.doctor_id == doctor_id,
            extract('month', Shift.date) == prev_month,
            extract('year', Shift.date) == prev_year,
            Shift.status.in_(["scheduled", "completed", "paid"])
        ).all()
        prev_total_value = 0
        prev_total_hours = 0
        for shift in prev_shifts:
            start_seconds = shift.start_time.hour * 3600 + shift.start_time.minute * 60 + shift.start_time.second
            end_seconds = shift.end_time.hour * 3600 + shift.end_time.minute * 60 + shift.end_time.second
            if end_seconds < start_seconds:
                end_seconds += 24 * 3600
            hours = (end_seconds - start_seconds) / 3600
            if hours > 0:
                prev_total_value += float(shift.value)
                prev_total_hours += hours
        previous_avg_hourly_rate = prev_total_value / prev_total_hours if prev_total_hours > 0 else 0

        return {
            "monthly_earnings": monthly_earnings_f,
            "previous_month_earnings": previous_month_earnings_f,
            "expenses_total": expenses_total,
            "previous_expenses_total": previous_expenses_total,
            "net": monthly_earnings_f - expenses_total,
            "previous_net": previous_month_earnings_f - previous_expenses_total,
            "scheduled_shifts": scheduled_shifts,
            "previous_scheduled_shifts": previous_scheduled_shifts,
            "hours_worked": round(hours_worked, 1),
            "previous_hours_worked": round(previous_hours_worked, 1),
            "avg_hourly_rate": round(avg_hourly_rate, 2),
            "previous_avg_hourly_rate": round(previous_avg_hourly_rate, 2)
        }
        
    def get_financial_chart_data(self, db: Session, doctor_id: int) -> list:
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        current_year = datetime.now(brazil_tz).year
        
        results = db.query(
            extract('month', Shift.payment_date).label('month'),
            func.sum(Shift.value).label('earnings'),
            func.count(Shift.id).label('shifts_count')
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('year', Shift.payment_date) == current_year,
            Shift.status == "paid",
            Shift.payment_date.isnot(None)
        ).group_by(
            extract('month', Shift.payment_date)
        ).order_by(
            extract('month', Shift.payment_date)
        ).all()

        monthly_data = []
        for month in range(1, 13):
            month_data = next((r for r in results if r.month == month), None)
            monthly_data.append({
                'month': month,
                'earnings': float(month_data.earnings) if month_data else 0,
                'shifts_count': month_data.shifts_count if month_data else 0
            })

        return monthly_data
    
    def get_financial_data(self, db: Session, doctor_id: int, year: int) -> dict:
        monthly_data = self.get_monthly_financial_data(db, doctor_id, year)
        
        totals = self.get_annual_totals(db, doctor_id, year)
        
        return {
            "monthly_data": monthly_data,
            "annual_totals": totals
        }

    def get_monthly_financial_data(self, db: Session, doctor_id: int, year: int) -> list:
        completed_shifts = db.query(
            extract('month', Shift.date).label('month'),
            func.sum(Shift.value).label('received'),
            func.count(Shift.id).label('completed_shifts')
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('year', Shift.date) == year,
            Shift.status.in_(["scheduled", "paid", "completed", ])
        ).group_by(
            extract('month', Shift.date)
        ).all()

        scheduled_shifts = db.query(
            extract('month', Shift.date).label('month'),
            func.sum(Shift.value).label('expected'),
            func.count(Shift.id).label('scheduled_shifts')
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('year', Shift.date) == year,
            Shift.status == "scheduled"
        ).group_by(
            extract('month', Shift.date)
        ).all()

        expenses_by_month = db.query(
            extract("month", ShiftExpense.expense_date).label("month"),
            func.coalesce(func.sum(ShiftExpense.amount), 0).label("expenses_total"),
        ).filter(
            ShiftExpense.doctor_id == doctor_id,
            extract("year", ShiftExpense.expense_date) == year,
        ).group_by(
            extract("month", ShiftExpense.expense_date)
        ).all()

        monthly_data = []
        for month in range(1, 13):
            completed = next((r for r in completed_shifts if r.month == month), None)
            scheduled = next((r for r in scheduled_shifts if r.month == month), None)
            expense_row = next((r for r in expenses_by_month if r.month == month), None)
            
            received = float(completed.received) if completed else 0
            completed_count = completed.completed_shifts if completed else 0
            expected = float(scheduled.expected) if scheduled else 0
            scheduled_count = scheduled.scheduled_shifts if scheduled else 0
            expenses_total = float(expense_row.expenses_total) if expense_row else 0
            expected_total = expected + received
            
            monthly_data.append({
                'month': month,
                'received': received,
                'expected': expected_total,
                'expenses_total': expenses_total,
                'net': expected_total - expenses_total,
                'shifts': completed_count + scheduled_count,
                'avg_per_shift': received / completed_count if completed_count > 0 else 0
            })

        return monthly_data

    def get_annual_totals(self, db: Session, doctor_id: int, year: int) -> dict:
        total_received = db.query(
            func.coalesce(func.sum(Shift.value), 0)
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('year', Shift.date) == year,
            Shift.status.in_(["scheduled", "paid", "completed"])
        ).scalar()

        total_expected = db.query(
            func.coalesce(func.sum(Shift.value), 0)
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('year', Shift.date) == year,
            or_(
                Shift.status == "scheduled",
                Shift.status.in_(["scheduled", "paid", "completed"])
            )
        ).scalar()

        total_shifts = db.query(
            func.count(Shift.id)
        ).filter(
            Shift.doctor_id == doctor_id,
            extract('year', Shift.date) == year,
            or_(
                Shift.status == "scheduled",
                Shift.status.in_(["scheduled", "paid", "completed"])
            )
        ).scalar()

        total_expenses = db.query(
            func.coalesce(func.sum(ShiftExpense.amount), 0)
        ).filter(
            ShiftExpense.doctor_id == doctor_id,
            extract("year", ShiftExpense.expense_date) == year,
        ).scalar()

        total_expected_f = float(total_expected)
        total_expenses_f = float(total_expenses)

        return {
            'total_received': float(total_received),
            'total_expected': total_expected_f,
            'total_expenses': total_expenses_f,
            'total_net': total_expected_f - total_expenses_f,
            'total_shifts': total_shifts,
            'avg_per_shift': float(total_received) / total_shifts if total_shifts > 0 else 0
        }

    def update_status(self, db: Session, shift: Shift, status: str) -> Shift:
        shift.status = status
        db.commit()
        db.refresh(shift)
        return shift
        
    def delete_shift(self, db: Session, shift_id: int) -> bool:
        shift = self.get_by_id(db, shift_id)
        if not shift:
            return False
        
        if shift.payment:
            db.delete(shift.payment)

        for expense in list(shift.expenses or []):
            db.delete(expense)

        db.delete(shift)
        db.commit()
        return True
        
    def update(self, db: Session, shift: Shift, update_data) -> Shift:
        for field, value in update_data.__dict__.items():
            if value is not None:
                setattr(shift, field, value)
        db.commit()
        db.refresh(shift)
        return shift
        