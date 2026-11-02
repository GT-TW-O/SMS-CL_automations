import os
import re
import csv
import datetime
import urllib.parse
import glob
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
import functions_framework
import google.auth
from flask import redirect, make_response, jsonify, Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

FOLDER_NAME = 'SMSB&RP'
SERVICE_URL = 'https://process-sms-backups-a6zg62zeqa-ts.a.run.app'

CLOSING_PATTERN = re.compile(
    r'^(thanks|thank you|thx|ty|ok|okay|k|cheers|ta|sounds good|great|awesome|'
    r'perfect|no worries|nw|all good|see you then|see ya|will do|got it|sweet|'
    r'cool|👍|👌|🙏|❤️|😂|😊)[\s\.\!\,]*$',
    re.IGNORECASE
)

SPAM_KEYWORDS = re.compile(
    r'(verification code|security code|one-time|otp|opt out|reply stop|'
    r'unsub|do not reply|norep|auspost|mygov|afterpay|zip pay|uber|deliveroo)',
    re.IGNORECASE
)

def clean_snippet(text):
    if not text:
        return ''
    s = str(text).replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def normalize_phone(num):
    if pd.isna(num) or not str(num).strip():
        return 'Unknown'
    s = str(num).strip()
    if any(c.isalpha() for c in s):
        return s
    cleaned = re.sub(r'[^\d+]', '', s)
    if not cleaned:
        return s
    if cleaned.startswith('0011'):
        cleaned = '+' + cleaned[4:]
    elif cleaned.startswith('0') and len(cleaned) == 10:
        cleaned = '+61' + cleaned[1:]
    elif cleaned.startswith('61') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    elif len(cleaned) == 9 and cleaned.startswith('4'):
        cleaned = '+61' + cleaned
    return cleaned

def is_closing_msg(body):
    text = str(body).strip()
    if '?' in text:
        return False
    if len(text.split()) <= 5 and CLOSING_PATTERN.match(text):
        return True
    return False

def download_file(drive_service, file_id, local_path):
    request = drive_service.files().get_media(fileId=file_id)
    with open(local_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request, chunksize=50 * 1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()

@functions_framework.http
def process_backups(request):
    sms_target = request.args.get('sms')
    if sms_target:
        cleaned_target = re.sub(r'[^\d+]', '', sms_target)
        html_redirect = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0;url=sms:{cleaned_target}">
    <script>
        window.location.href = "sms:{cleaned_target}";
        setTimeout(function() {{ window.close(); }}, 1500);
    </script>
</head>
<body style="font-family:sans-serif;text-align:center;padding-top:40px;">
    <p>Opening SMS to <b>{cleaned_target}</b>...</p>
    <p><a href="sms:{cleaned_target}" style="font-size:18px;color:#1a73e8;font-weight:bold;">Tap here if your messaging app did not open</a></p>
</body>
</html>"""
        response = make_response(html_redirect, 200)
        response.headers['Content-Type'] = 'text/html'
        return response

    try:
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/drive.readonly'])
        drive_service = build('drive', 'v3', credentials=creds)

        folder_q = f"name = '{FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = drive_service.files().list(q=folder_q, fields="files(id)").execute().get('files', [])
        if not folders:
            return {"status": "error", "message": f"Folder '{FOLDER_NAME}' not found in Drive."}, 404
        folder_id = folders[0]['id']

        sms_q = f"'{folder_id}' in parents and name contains 'sms-' and name contains '.xml' and trashed = false"
        calls_q = f"'{folder_id}' in parents and name contains 'calls-' and name contains '.xml' and trashed = false"
        sms_files = drive_service.files().list(q=sms_q, orderBy="createdTime desc", pageSize=50, fields="files(id, name, createdTime)").execute().get('files', [])
        calls_files = drive_service.files().list(q=calls_q, orderBy="createdTime desc", pageSize=1, fields="files(id, name, createdTime)").execute().get('files', [])

        if not sms_files or not calls_files:
            return {"status": "error", "message": "Missing sms-*.xml or calls-*.xml backup files."}, 404

        latest_calls = calls_files[0]
        local_calls_xml = '/tmp/latest_calls.xml'
        download_file(drive_service, latest_calls['id'], local_calls_xml)

        # --- MODE 1: Interactive Contact Message Search (Scans ALL historical SMS XML backups) ---
        phone_query = request.args.get('phone')
        name_query = request.args.get('name')
        if phone_query or name_query:
            limit = int(request.args.get('limit', 10))
            matched_messages = []
            
            # Download and scan all historical sms-*.xml files present in Drive
            for sms_file in sms_files:
                temp_xml_path = f"/tmp/{sms_file['name']}"
                if not os.path.exists(temp_xml_path):
                    download_file(drive_service, sms_file['id'], temp_xml_path)
                
                for event, elem in ET.iterparse(temp_xml_path, events=('end',)):
                    if elem.tag == 'sms':
                        addr = elem.attrib.get('address', '')
                        contact = elem.attrib.get('contact_name', '(Unknown)')
                        body = clean_snippet(elem.attrib.get('body', ''))
                        date_str = elem.attrib.get('readable_date', '')
                        msg_type = 'Received' if elem.attrib.get('type') == '1' else 'Sent'
                        
                        match_found = False
                        if phone_query and phone_query in addr:
                            match_found = True
                        if name_query and name_query.lower() in contact.lower():
                            match_found = True
                            
                        if match_found:
                            matched_messages.append({
                                'readable_date': date_str,
                                'address': addr,
                                'contact_name': contact,
                                'type': msg_type,
                                'body': body
                            })
                    elif elem.tag in ('mms', 'part', 'parts', 'addr', 'addrs'):
                        elem.clear()

            # Deduplicate and sort chronologically
            seen = set()
            unique_messages = []
            for m in matched_messages:
                identifier = (m['readable_date'], m['body'])
                if identifier not in seen:
                    seen.add(identifier)
                    unique_messages.append(m)

            unique_messages.sort(key=lambda x: x['readable_date'])
            results = unique_messages[-limit:] if len(unique_messages) >= limit else unique_messages

            return jsonify({
                "query": {"phone": phone_query, "name": name_query},
                "total_found": len(unique_messages),
                "returned": len(results),
                "messages": results
            }), 200

        # --- MODE 2: Daily Follow-Up Digest Generation (Uses latest XML) ---
        latest_sms = sms_files[0]
        local_sms_xml = '/tmp/latest_sms.xml'
        download_file(drive_service, latest_sms['id'], local_sms_xml)

        sms_rows = []
        for event, elem in ET.iterparse(local_sms_xml, events=('end',)):
            if elem.tag == 'sms':
                msg_type = 'Received' if elem.attrib.get('type') == '1' else 'Sent'
                addr = elem.attrib.get('address', '')
                norm = normalize_phone(addr)
                sms_rows.append({
                    'readable_date': elem.attrib.get('readable_date', ''),
                    'address': addr,
                    'norm_number': norm,
                    'contact_name': elem.attrib.get('contact_name', '(Unknown)'),
                    'type': msg_type,
                    'body': clean_snippet(elem.attrib.get('body', ''))
                })
                elem.clear()
            elif elem.tag in ('mms', 'part', 'parts', 'addr', 'addrs'):
                elem.clear()

        call_rows = []
        for event, elem in ET.iterparse(local_calls_xml, events=('end',)):
            if elem.tag == 'call':
                num = elem.attrib.get('number', '')
                norm = normalize_phone(num)
                call_rows.append({
                    'readable_date': elem.attrib.get('readable_date', ''),
                    'number': num,
                    'norm_number': norm,
                    'contact_name': elem.attrib.get('contact_name', '(Unknown)'),
                    'call_type': elem.attrib.get('type', ''),
                    'duration': int(elem.attrib.get('duration', 0))
                })
                elem.clear()

        df_sms = pd.DataFrame(sms_rows)
        df_calls = pd.DataFrame(call_rows)

        df_sms['dt'] = pd.to_datetime(df_sms['readable_date'], errors='coerce')
        df_calls['dt'] = pd.to_datetime(df_calls['readable_date'], errors='coerce')
        df_sms = df_sms.dropna(subset=['dt']).sort_values('dt')
        df_calls = df_calls.dropna(subset=['dt']).sort_values('dt')

        name_map = {}
        for df in [df_sms, df_calls]:
            valid = df[~df['contact_name'].isin(['(Unknown)', '', 'null', None])]
            for n, c in zip(valid['norm_number'], valid['contact_name']):
                name_map[n] = c

        vip_counts = df_sms['norm_number'].value_counts().add(df_calls['norm_number'].value_counts(), fill_value=0).to_dict()
        ref_now = max(df_sms['dt'].max(), df_calls['dt'].max())

        last_outbound_sms = df_sms[df_sms['type'] == 'Sent'].groupby('norm_number')['dt'].max().to_dict()
        last_connected_or_out_call = df_calls[
            (df_calls['call_type'] == '2') | ((df_calls['call_type'] == '1') & (df_calls['duration'] > 10))
        ].groupby('norm_number')['dt'].max().to_dict()

        queue_items = []
        missed_df = df_calls[df_calls['call_type'].isin(['3', '5'])]
        
        for num, group in missed_df.groupby('norm_number'):
            if any(c.isalpha() for c in str(num)) and num != 'Unknown':
                continue
            last_miss_dt = group['dt'].max()
            age_days = (ref_now - last_miss_dt).total_seconds() / 86400.0
            if age_days > 90:
                continue
            res_sms = last_outbound_sms.get(num, pd.Timestamp.min)
            res_call = last_connected_or_out_call.get(num, pd.Timestamp.min)
            if max(res_sms, res_call) < last_miss_dt:
                queue_items.append({
                    'norm_number': num,
                    'contact_name': name_map.get(num, '(Unknown)'),
                    'category': 'Action Required',
                    'item_type': 'Missed Call',
                    'timestamp': last_miss_dt,
                    'age_days': age_days,
                    'snippet': f"Missed call ({len(group[group['dt'] == last_miss_dt])} attempt)",
                    'vip_score': int(vip_counts.get(num, 1))
                })

        for num, group in df_sms.groupby('norm_number'):
            if any(c.isalpha() for c in str(num)) or len(re.sub(r'[^\d]', '', str(num))) < 8:
                continue
            last_row = group.iloc[-1]
            last_dt = last_row['dt']
            age_days = (ref_now - last_dt).total_seconds() / 86400.0
            body = str(last_row['body']).strip()
            ever_sent = (group['type'] == 'Sent').any()

            if last_row['type'] == 'Received':
                if age_days > 90:
                    continue
                if not ever_sent and SPAM_KEYWORDS.search(body):
                    continue
                res_call = last_connected_or_out_call.get(num, pd.Timestamp.min)
                if res_call > last_dt:
                    continue
                if is_closing_msg(body):
                    continue
                queue_items.append({
                    'norm_number': num,
                    'contact_name': name_map.get(num, '(Unknown)'),
                    'category': 'Action Required',
                    'item_type': 'Unanswered SMS',
                    'timestamp': last_dt,
                    'age_days': age_days,
                    'snippet': body,
                    'vip_score': int(vip_counts.get(num, 1))
                })
            elif last_row['type'] == 'Sent':
                if 3.0 <= age_days <= 14.0 and '?' in body:
                    res_call = last_connected_or_out_call.get(num, pd.Timestamp.min)
                    if res_call <= last_dt:
                        queue_items.append({
                            'norm_number': num,
                            'contact_name': name_map.get(num, '(Unknown)'),
                            'category': 'Ball in Their Court',
                            'item_type': 'Awaiting Their Reply',
                            'timestamp': last_dt,
                            'age_days': age_days,
                            'snippet': body,
                            'vip_score': int(vip_counts.get(num, 1))
                        })

        df_queue = pd.DataFrame(queue_items)

        def assign_bucket(row):
            if row['category'] == 'Ball in Their Court':
                return '5. Ball in Their Court (3–14 Days)'
            d = row['age_days']
            if d <= 1.0:
                return '1. Previous Day (Last 24h)'
            elif d <= 7.0:
                return '2. Previous Week (2–7 Days)'
            elif d <= 30.0:
                return '3. Previous Month (8–30 Days)'
            else:
                return '4. Previous Three Months (31–90 Days)'

        if not df_queue.empty:
            df_queue['bucket'] = df_queue.apply(assign_bucket, axis=1)
            df_queue = df_queue.sort_values('timestamp', ascending=False).drop_duplicates(subset=['norm_number', 'category'])
            df_queue = df_queue.sort_values(['bucket', 'vip_score', 'timestamp'], ascending=[True, False, False])
        else:
            df_queue = pd.DataFrame(columns=['bucket', 'norm_number', 'contact_name', 'category', 'item_type', 'timestamp', 'age_days', 'snippet', 'vip_score'])

        base_url = request.base_url.rstrip('/') if request.base_url else SERVICE_URL
        if base_url.startswith('http://'):
            base_url = 'https://' + base_url[7:]

        html = build_html_digest(df_queue, ref_now, base_url)
        return {"status": "ok", "html": html, "count": len(df_queue)}, 200

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return {"status": "error", "message": error_msg}, 500

def build_html_digest(df_queue, ref_now, base_url):
    buckets = [
        '1. Previous Day (Last 24h)',
        '2. Previous Week (2–7 Days)',
        '3. Previous Month (8–30 Days)',
        '4. Previous Three Months (31–90 Days)',
        '5. Ball in Their Court (3–14 Days)'
    ]
    parts = [
        f"<div style='font-family:Arial,sans-serif;color:#222;max-width:1250px;'>",
        f"<h2 style='font-size:24px;'>Daily SMS & Call Follow-Up Digest</h2>",
        f"<p style='color:#666;font-size:20px;'>-{ref_now.strftime('%Y-%m-%d')} - {ref_now.strftime('%H%M')}</p>"
    ]
    
    parts.append("<table style='width:1250px;table-layout:fixed;border-collapse:collapse;font-size:17px;'>")
    parts.append("<tr style='height:0px;line-height:0px;'>"
                 "<th style='padding:0;border:0;width:250px;'></th>"
                 "<th style='padding:0;border:0;width:150px;'></th>"
                 "<th style='padding:0;border:0;width:150px;'></th>"
                 "<th style='padding:0;border:0;width:150px;'></th>"
                 "<th style='padding:0;border:0;width:600px;'></th>"
                 "<th style='padding:0;border:0;width:50px;'></th>"
                 "</tr>")

    for b in buckets:
        sub = df_queue[df_queue['bucket'] == b] if not df_queue.empty else pd.DataFrame()
        parts.append(f"<tr><td colspan='6' align='left' style='background:#f4f6f8;padding:12px;border-top:1px solid #dcdcdc;border-bottom:1px solid #dcdcdc;border-left:4px solid #1a73e8;font-weight:bold;font-size:19px;text-align:left;'>{b} ({len(sub)})</td></tr>")
        
        if sub.empty:
            parts.append(f"<tr><td colspan='6' align='left' style='padding:8px 12px;border-bottom:1px solid #dcdcdc;color:#777;font-size:17px;text-align:left;'>No items in this window.</td></tr>")
            continue
            
        for _, r in sub.iterrows():
            num = r['norm_number']
            ts = pd.to_datetime(r['timestamp'])
            dt_str = f"-{ts.strftime('%Y-%m-%d')}<br>{ts.strftime('%H%M')}"
            
            encoded_num = urllib.parse.quote(str(num))
            sms_https_url = f"{base_url}?sms={encoded_num}"
            
            action_links = (
                f"<a href='tel:{num}' style='color:#1a73e8;text-decoration:none;font-weight:bold;'>Call</a>"
                f"&nbsp;|&nbsp;"
                f"<a href='{sms_https_url}' target='_blank' style='color:#1a73e8;text-decoration:none;font-weight:bold;'>SMS</a>"
            )

            parts.append(
                f"<tr style='border-bottom:1px solid #dcdcdc;'>"
                f"<td style='padding:8px 10px;width:250px;word-break:break-word;overflow:hidden;'><b>{r['contact_name']}</b><br><span style='color:#666;font-size:15px;'>{num}</span></td>"
                f"<td align='center' style='padding:8px 10px;width:150px;text-align:center;overflow:hidden;'>{r['item_type']}</td>"
                f"<td align='center' style='padding:8px 10px;width:150px;white-space:nowrap;text-align:center;overflow:hidden;'>{dt_str}</td>"
                f"<td align='center' style='padding:8px 10px;width:150px;white-space:nowrap;text-align:center;overflow:hidden;'>{action_links}</td>"
                f"<td style='padding:8px 10px;width:600px;word-break:break-word;overflow:hidden;'>{r['snippet']}</td>"
                f"<td align='center' style='padding:8px 10px;width:50px;white-space:nowrap;text-align:center;overflow:hidden;'>{r['vip_score']}</td>"
                f"</tr>"
            )
            
    parts.append("</table>")
    parts.append("</div>")
    return "".join(parts)
