from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.importer import ImportError_, existing_financial_year, import_workbook, peek_workbook_identity
from app.models import Entity
from app.templating import templates

router = APIRouter()

_PENDING: dict[str, bytes] = {}


@router.get("/import")
def import_form(request: Request, db: Session = Depends(get_db)):
    entities = db.query(Entity).order_by(Entity.company_name).all()
    return templates.TemplateResponse("import_upload.html", {"request": request, "entities": entities})


@router.post("/import")
async def handle_import(request: Request, file: UploadFile, entity_id: str = "", db: Session = Depends(get_db)):
    content = await file.read()
    eid = int(entity_id) if entity_id else None

    try:
        identity = peek_workbook_identity(content)
    except Exception as e:
        entities = db.query(Entity).order_by(Entity.company_name).all()
        return templates.TemplateResponse(
            "import_upload.html",
            {"request": request, "entities": entities, "error": f"Could not read workbook: {e}"},
        )

    entity = None
    if eid:
        entity = db.get(Entity, eid)
    if entity is None and identity.get("registration_number"):
        entity = db.query(Entity).filter_by(registration_number=identity["registration_number"]).one_or_none()

    existing_fy = None
    if entity and identity.get("year_end_date"):
        existing_fy = existing_financial_year(db, entity.id, identity["year_end_date"])

    if existing_fy is not None:
        token = f"{entity.id}-{identity['year_end_date'].isoformat()}"
        _PENDING[token] = content
        return templates.TemplateResponse(
            "import_confirm.html",
            {
                "request": request,
                "identity": identity,
                "entity": entity,
                "token": token,
            },
        )

    fy = import_workbook(db, content, entity_id=eid)
    return RedirectResponse(f"/years/{fy.id}", status_code=303)


@router.post("/import/confirm")
async def confirm_import(request: Request, token: str, entity_id: str, db: Session = Depends(get_db)):
    content = _PENDING.pop(token, None)
    if content is None:
        return RedirectResponse("/import", status_code=303)
    eid = int(entity_id) if entity_id else None
    fy = import_workbook(db, content, entity_id=eid)
    return RedirectResponse(f"/years/{fy.id}", status_code=303)
