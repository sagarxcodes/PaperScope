from fastapi import APIRouter, UploadFile, File, HTTPException

from app.routers.material import extract_text
from app.engines.pyq_intelligence_engine import analyze_pyq_documents
from app.engines.prediction_engine import generate_predicted_paper, generate_revision_notes


router = APIRouter(
    prefix="/api/pyq",
    tags=["PYQ Intelligence"],
)


@router.post("/analyze")
async def analyze_pyq(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(
            status_code=400,
            detail="At least one PYQ file is required."
        )

    documents = []

    for file in files:
        data = await file.read()

        if not data:
            continue

        filename = file.filename or "unknown.txt"

        try:
            text = extract_text(filename, data)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not process {filename}: {exc}"
            )

        if not text.strip():
            continue

        documents.append({
            "filename": filename,
            "text": text,
        })

    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No readable PYQ documents were found."
        )

    result = analyze_pyq_documents(documents)

    prediction = generate_predicted_paper(
        result,
        max_questions=10,
    )

    revision_notes = generate_revision_notes(result)

    result["prediction"] = prediction
    result["predicted_paper"] = prediction
    result["revision_notes"] = revision_notes

    return result
