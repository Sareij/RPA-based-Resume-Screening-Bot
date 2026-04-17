"""
Flask Routes — All CHIS Web Endpoints
"""

import os
import json
import uuid
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, jsonify)
from werkzeug.utils import secure_filename

from .modules.ocr_extractor  import extract_text_from_file, clean_text
from .modules.nlp_parser      import parse_resume
from .modules.bias_detector   import detect_bias_indicators, create_blind_resume, get_bias_summary
from .modules.jd_parser       import parse_job_description, compute_jd_match
from .modules.ml_scorer       import (rank_candidates, generate_explanation,
                                       cluster_candidates, get_cluster_summary,
                                       compute_growth_potential, detect_fraud)

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# In-memory session store (use DB for production)
_SESSION_STORE = {}


# ─────────────────────────────────────────────────────────────
# HOME / DASHBOARD
# ─────────────────────────────────────────────────────────────

@main.route('/')
def index():
    return render_template('index.html')


# ─────────────────────────────────────────────────────────────
# STEP 1: UPLOAD JOB DESCRIPTION
# ─────────────────────────────────────────────────────────────

@main.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        jd_text = request.form.get('jd_text', '').strip()
        blind_mode = 'blind_mode' in request.form

        if not jd_text:
            flash('Please enter a Job Description.', 'danger')
            return redirect(url_for('main.setup'))

        parsed_jd = parse_job_description(jd_text)
        session_id = str(uuid.uuid4())[:8]
        _SESSION_STORE[session_id] = {
            'jd': parsed_jd,
            'blind_mode': blind_mode,
            'candidates': [],
        }
        session['sid'] = session_id
        flash(f'JD parsed successfully! Detected role: {parsed_jd["role_category"]}', 'success')
        return redirect(url_for('main.upload_resumes'))

    return render_template('setup.html')


# ─────────────────────────────────────────────────────────────
# STEP 2: UPLOAD RESUMES
# ─────────────────────────────────────────────────────────────

@main.route('/upload', methods=['GET', 'POST'])
def upload_resumes():
    sid = session.get('sid')
    if not sid or sid not in _SESSION_STORE:
        flash('Please set up a Job Description first.', 'warning')
        return redirect(url_for('main.setup'))

    store = _SESSION_STORE[sid]

    if request.method == 'POST':
        files = request.files.getlist('resumes')
        if not files or all(f.filename == '' for f in files):
            flash('No files selected.', 'danger')
            return redirect(url_for('main.upload_resumes'))

        upload_folder = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
        processed = 0

        for file in files:
            if file and allowed_file(file.filename):
                filename  = secure_filename(file.filename)
                filepath  = os.path.join(upload_folder, filename)
                file.save(filepath)

                # Full processing pipeline
                raw_text     = extract_text_from_file(filepath)
                clean        = clean_text(raw_text)
                parsed       = parse_resume(clean if clean else raw_text)
                bias         = detect_bias_indicators(parsed)
                blind        = create_blind_resume(parsed, bias) if store['blind_mode'] else None
                match_result = compute_jd_match(
                    blind if (blind and store['blind_mode']) else parsed,
                    store['jd'],
                    blind_mode=store['blind_mode']
                )
                growth       = compute_growth_potential(parsed)
                fraud        = detect_fraud(parsed)
                bias_summary = get_bias_summary(bias)

                store['candidates'].append({
                    'filename':     filename,
                    'parsed_resume': parsed,
                    'blind_resume': blind,
                    'bias_report':  bias,
                    'bias_summary': bias_summary,
                    'match_result': match_result,
                    'growth':       growth,
                    'fraud':        fraud,
                })
                processed += 1

        if processed == 0:
            flash('No valid resume files found. Supported: PDF, DOCX, PNG, JPG', 'danger')
        else:
            flash(f'{processed} resume(s) processed successfully!', 'success')
            return redirect(url_for('main.results'))

    return render_template('upload.html', store=store)


# ─────────────────────────────────────────────────────────────
# STEP 3: RESULTS + EXPLAINABLE AI DASHBOARD
# ─────────────────────────────────────────────────────────────

@main.route('/results')
def results():
    sid = session.get('sid')
    if not sid or sid not in _SESSION_STORE:
        return redirect(url_for('main.setup'))

    store = _SESSION_STORE[sid]
    candidates = store.get('candidates', [])

    if not candidates:
        flash('No candidates processed yet.', 'warning')
        return redirect(url_for('main.upload_resumes'))

    # Rank all candidates
    ranked = rank_candidates(candidates)
    clusters = cluster_candidates(ranked)
    cluster_summary = get_cluster_summary(clusters)

    return render_template('results.html',
        ranked=ranked,
        jd=store['jd'],
        blind_mode=store['blind_mode'],
        clusters=cluster_summary,
        total=len(ranked),
    )


# ─────────────────────────────────────────────────────────────
# CANDIDATE DETAIL VIEW
# ─────────────────────────────────────────────────────────────

@main.route('/candidate/<int:rank>')
def candidate_detail(rank):
    sid = session.get('sid')
    if not sid or sid not in _SESSION_STORE:
        return redirect(url_for('main.setup'))

    store = _SESSION_STORE[sid]
    candidates = store.get('candidates', [])
    ranked = rank_candidates(candidates)

    if rank < 1 or rank > len(ranked):
        flash('Candidate not found.', 'danger')
        return redirect(url_for('main.results'))

    cand = ranked[rank - 1]
    return render_template('candidate_detail.html',
        cand=cand,
        jd=store['jd'],
        blind_mode=store['blind_mode'],
        rank=rank,
        total=len(ranked),
    )


# ─────────────────────────────────────────────────────────────
# RESET SESSION
# ─────────────────────────────────────────────────────────────

@main.route('/reset')
def reset():
    sid = session.get('sid')
    if sid and sid in _SESSION_STORE:
        del _SESSION_STORE[sid]
    session.clear()
    flash('Session reset. Start a new screening round.', 'info')
    return redirect(url_for('main.index'))


# ─────────────────────────────────────────────────────────────
# API: Export results as JSON
# ─────────────────────────────────────────────────────────────

@main.route('/api/export')
def export_json():
    sid = session.get('sid')
    if not sid or sid not in _SESSION_STORE:
        return jsonify({'error': 'No session'}), 400

    store = _SESSION_STORE[sid]
    candidates = store.get('candidates', [])
    ranked = rank_candidates(candidates)

    export = []
    for c in ranked:
        pr = c['parsed_resume']
        export.append({
            'rank':          c['rank'],
            'name':          pr.get('name', 'Unknown'),
            'email':         pr.get('email', ''),
            'overall_score': c['match_result']['overall_score'],
            'skills':        pr.get('skills', []),
            'experience':    pr.get('experience_years', 0),
            'growth_score':  c['growth']['score'],
            'fraud_risk':    c['fraud']['risk_level'],
            'bias_score':    c['bias_report']['bias_score'],
            'cluster':       c.get('cluster', 'Unknown'),
        })

    return jsonify({'candidates': export, 'job': store['jd'].get('title', '')})
