/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * FileAttachRestlet — upload a file to the File Cabinet and optionally attach
 * it to a record. Fills the gap left by NetSuite's REST Record API, which has
 * no File Cabinet support.
 *
 * POST body (JSON):
 * {
 *   "filename":      "workpaper.xlsx",
 *   "contentBase64": "<base64-encoded file bytes>",
 *   "folderId":      1234,                // required: File Cabinet folder internal id
 *   "recordType":    "journalentry",      // optional; if present with recordId, attaches
 *   "recordId":      4242,
 *   "description":   "Supporting workpaper"  // optional
 * }
 *
 * Response: { "success": true, "fileId": 12345, "attached": true }
 *        or { "success": false, "error": "..." }
 *
 * Binary file types (xlsx, pdf, png, ...) MUST be sent as base64 in
 * "contents" — that is the only representation N/file accepts for them.
 * Keep request payloads under ~9 MB: base64 inflates bytes ~33% and the
 * RESTlet request limit is ~10 MB.
 */
define(['N/file', 'N/record', 'N/log'], (file, record, log) => {

    const TYPE_BY_EXT = {
        xlsx: file.Type.EXCEL,
        xls:  file.Type.EXCEL,
        csv:  file.Type.CSV,
        pdf:  file.Type.PDF,
        txt:  file.Type.PLAINTEXT,
        json: file.Type.JSON,
        png:  file.Type.PNGIMAGE,
        jpg:  file.Type.JPGIMAGE,
        jpeg: file.Type.JPGIMAGE,
        zip:  file.Type.ZIP,
        docx: file.Type.WORD,
        doc:  file.Type.WORD
    };

    const post = (body) => {
        try {
            if (!body.filename || !body.contentBase64) {
                return { success: false, error: 'filename and contentBase64 are required' };
            }

            const folderId = parseInt(body.folderId, 10);
            if (!folderId) {
                return { success: false, error: 'folderId is required (File Cabinet folder internal id)' };
            }

            const ext = body.filename.split('.').pop().toLowerCase();
            const fileType = TYPE_BY_EXT[ext];
            if (!fileType) {
                return { success: false, error: `Unsupported file extension: ${ext}` };
            }

            const f = file.create({
                name: body.filename,
                fileType: fileType,
                contents: body.contentBase64, // base64 for binary types
                folder: folderId,
                description: body.description || '',
                encoding: file.Encoding.UTF8
            });
            const fileId = f.save();

            let attached = false;
            if (body.recordType && body.recordId) {
                record.attach({
                    record: { type: 'file', id: fileId },
                    to: { type: String(body.recordType), id: parseInt(body.recordId, 10) }
                });
                attached = true;
            }

            log.audit('FileAttachRestlet', `file ${fileId} (${body.filename}) attached=${attached} to ${body.recordType}/${body.recordId}`);
            return { success: true, fileId: fileId, attached: attached };

        } catch (e) {
            log.error('FileAttachRestlet failed', e);
            return { success: false, error: `${e.name}: ${e.message}` };
        }
    };

    return { post };
});
