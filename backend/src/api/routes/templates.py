import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.credentials import (
    delete_custom_template,
    list_custom_templates,
    save_custom_template,
)
from api.s3 import generate_upload_url
from etsy_assistant.steps.mockup import list_templates as list_bundled_templates

router = APIRouter()


class TemplateItem(BaseModel):
    id: str
    name: str
    orientation: str = "vertical"
    is_custom: bool = False
    s3_key: str | None = None
    frame_bbox: list[int] | None = None


class ListTemplatesResponse(BaseModel):
    templates: list[TemplateItem]


class UploadTemplateRequest(BaseModel):
    name: str
    s3_key: str
    orientation: str = "vertical"


class UploadTemplateResponse(BaseModel):
    template: TemplateItem
    upload_url: str | None = None


@router.get("/templates", response_model=ListTemplatesResponse)
def get_templates():
    """List all available templates (bundled + custom)."""
    # Bundled templates
    bundled = [
        TemplateItem(id=name, name=name.replace("_", " "), is_custom=False)
        for name in list_bundled_templates()
    ]

    # Custom templates from DynamoDB
    custom = [
        TemplateItem(**item)
        for item in list_custom_templates()
    ]

    return ListTemplatesResponse(templates=bundled + custom)


@router.post("/templates/upload", response_model=UploadTemplateResponse)
def upload_template(
    content_type: str = Query(default="image/jpeg"),
):
    """Get a presigned URL to upload a custom frame template image."""
    template_id = uuid.uuid4().hex[:12]
    s3_key = f"templates/{template_id}"
    upload_url, _ = generate_upload_url(content_type)

    return UploadTemplateResponse(
        template=TemplateItem(id=template_id, name="", is_custom=True, s3_key=s3_key),
        upload_url=upload_url,
    )


@router.post("/templates", response_model=TemplateItem)
def save_template(req: UploadTemplateRequest):
    """Save custom template metadata after upload."""
    template_id = uuid.uuid4().hex[:12]
    item = save_custom_template(
        template_id=template_id,
        name=req.name,
        s3_key=req.s3_key,
        orientation=req.orientation,
    )
    return TemplateItem(**item)


@router.delete("/templates/{template_id}")
def remove_template(template_id: str):
    """Delete a custom template."""
    deleted = delete_custom_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}
