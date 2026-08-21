from sqlalchemy.orm import Session

from app.models import Item
from app.schemas import ItemCreate


def create_item(db: Session, item: ItemCreate) -> Item:
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def list_items(db: Session):
    return db.query(Item).order_by(Item.id).all()
