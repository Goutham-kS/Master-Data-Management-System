import datetime
import io
import math
import re
from flask import Blueprint, Response, current_app, render_template, request, redirect, flash, jsonify, send_file, session
from .database import get_db_connection
import pymysql

from flask import url_for

import os
import pandas as pd
from werkzeug.utils import secure_filename
from io import BytesIO
from flask import send_file
import csv

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

pharma_routes = Blueprint('pharma', __name__, template_folder='../templates')

ALLOWED_EXTENSIONS = {"xlsx"}

@pharma_routes.route('/')
def index():
    return render_template('index.html')

@pharma_routes.route('/search', methods=['GET', 'POST'])
def search_pharma_item():
    if request.method == 'POST':
        item_codes = (request.form.get("item_codes") or "").strip()
        mfg = (request.form.get("mfg") or "").strip()
        formulation = (request.form.get("formulation") or "").strip()
        description = (request.form.get("description") or "").strip()
        unit_names = request.form.getlist("unit_name[]")

        print("DEBUG: Item codes:", item_codes)
        print("DEBUG: MFG:", mfg)
        print("DEBUG: Formulation:", formulation)
        print("DEBUG: Description:", description)
        print("DEBUG: Unit Names:", unit_names)

        if not unit_names:
            flash("Please select at least one valid Unit Name!", "warning")
            print("WARNING: No unit names selected")
            return redirect(url_for('pharma.search_pharma_item'))

        if not any([item_codes, mfg, formulation, description]):
            flash("Please enter at least one search criterion!", "warning")
            print("WARNING: No search criteria provided")
            return redirect(url_for('pharma.search_pharma_item'))

        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed!", "danger")
            print("ERROR: DB connection failed")
            return redirect(url_for('pharma.index'))

        cursor = connection.cursor(pymysql.cursors.DictCursor)

        selected_units = ", ".join([f"`{unit}` AS `{unit}`" for unit in unit_names])
        query = f"""
            SELECT `ITEM_CODE`, `HSN_NO`, `DESCRIPTION`, `CATEGORY`, `MFG`, 
                    `PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY)`,
                    `PURCHASE_MRP_PER_UNIT_WITHOUT_TAX_FOR_(FY)`,
                    `BUOM`, `PUOM`, `GST_PERCENT`, `FORMULATION`, {selected_units}
            FROM itemmaster.pharmaitemdata
             WHERE ({' OR '.join([f'`{unit}` IS NOT NULL' for unit in unit_names])})
        """
        params = []

        if item_codes:
            code_list = item_codes.split()
            placeholders = ', '.join(['%s'] * len(code_list))
            query += f" AND `ITEM_CODE` IN ({placeholders})"
            params.extend(code_list)

        if mfg:
            query += " AND `MFG` LIKE %s"
            params.append(f"%{mfg}%")

        if formulation:
            query += " AND `FORMULATION` LIKE %s"
            params.append(f"%{formulation}%")

        if description:
            query += " AND `DESCRIPTION` LIKE %s"
            params.append(f"%{description}%")

        print("DEBUG: Final Query:", query)
        print("DEBUG: Query Params:", params)

        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            print("DEBUG: Results Count:", len(results))
        except Exception as e:
            flash(f"SQL Error: {str(e)}", "danger")
            print("ERROR:", str(e))
            return redirect(url_for('pharma.search_pharma_item'))
        finally:
            connection.close()

        if not results:
            flash("No records found matching your search criteria.", "info")
            print("INFO: No results found")
            return redirect(url_for('pharma.search_pharma_item'))

        session['search_results'] = results
        session['column_order'] = list(results[0].keys())
        return render_template('search_results.html', results=results)
    return render_template('search.html')




@pharma_routes.route('/insert', methods=['GET', 'POST'])
def insert_item():
    if request.method == 'POST':
        data = request.form.to_dict()

        # Format specific date fields
        for date_field in ['RC_EFFECTIVE_DATE_FROM', 'END_DATE']:
            if date_field in data and data[date_field]:
                try:
                    parsed_date = pd.to_datetime(data[date_field], errors='coerce')
                    if pd.notna(parsed_date):
                        data[date_field] = parsed_date.strftime('%d-%m-%Y')
                    else:
                        data[date_field] = None
                except Exception:
                    data[date_field] = None

        try:
            connection = get_db_connection()
            if connection is None:
                flash("Database connection failed.", "danger")
                return redirect(url_for('pharma_routes.insert_item'))

            cursor = connection.cursor()

            columns = ", ".join([f"`{col}`" for col in data.keys()])
            placeholders = ", ".join(["%s"] * len(data))
            values = tuple(data.values())

            query = f"INSERT INTO pharmaitemdata ({columns}) VALUES ({placeholders})"

            cursor.execute(query, values)
            connection.commit()
            print(current_app.url_map)
            flash("Item inserted successfully!", "success")
            return redirect(url_for('pharma.insert_item'))

        except pymysql.MySQLError as e:
            connection.rollback()
            flash(f"Database Error: {str(e)}", "danger")
            return redirect(url_for('pharma.insert_item'))


        finally:
            cursor.close()
            connection.close()

    return render_template('insert.html')


 

@pharma_routes.route("/bulk_insert", methods=["GET", "POST"])
def bulk_insert_pharma():
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part", "error")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("No selected file", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # Ensure uploads folder exists
            upload_folder = "uploads"
            os.makedirs(upload_folder, exist_ok=True)

            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            try:
                # Read Excel file
                df = pd.read_excel(filepath, dtype=str)
                df.dropna(how="all", inplace=True)

                # Clean column names
                df.columns = [col.strip() for col in df.columns]

                # ✅ Strip whitespace from string columns
                df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

                # ✅ Replace empty strings and NaN with None
                df.replace('', None, inplace=True)
                df = df.where(pd.notna(df), None)

                # ✅ Format date columns
                for date_col in ['RC_EFFECTIVE_DATE_FROM', 'END_DATE']:
                    if date_col in df.columns:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%d-%m-%Y')
                        df[date_col] = df[date_col].where(pd.notna(df[date_col]), None)

                # Required columns for pharmaitemdata
                required_columns = [
                    "FINANCIAL_YEAR","RC_EFFECTIVE_DATE_FROM","END_DATE","TYPE","FORMULATION","MFG","ARC_No","ITEM_CODE",
                    "DESCRIPTION","PACK_SIZE","PUOM","DENOMINATOR","NUMERATOR","BUOM","GST_PERCENT","PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY)",
                    "PURCHASE_PACK_PRICE_WITHOUT_TAX_FOR_(FY)","PURCHASE_MRP_PER_UNIT_WITHOUT_TAX_FOR_(FY)","PURCHASE_PACK_MRP_WITHOUT_TAX_FOR_(FY)",
                    "OFFERS","CATEGORY","HSN_NO","MHB1","MMB1","MWP1","MNB1","KMC1","MDP1","MGA1","MJP1","MSA1","MVJ1","MHSR","MHVR","MHPK","MHPB",
                    "MHYP","MHHB","MHDB","MHMY","MHGG","MHP1","MHGH","MHSL","MDHK","MSLA","MBBS","MMKA","MHKM","MEST","MPPP","MHNB","MHSB","MHMR",
                    "MHRA","MHRN","MHSG","MHRP","MHEC","CM_TEAM_HEAD"
                ]

                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f"Missing columns in file: {', '.join(missing_columns)}", "error")
                    return redirect(request.url)

                def sanitize_row(row):
                    return tuple(None if (x is None or (isinstance(x, float) and math.isnan(x))) else x for x in row)

                data_tuples = df[required_columns].apply(sanitize_row, axis=1).tolist()

                if not data_tuples:
                    flash("No valid data to insert.", "error")
                    return redirect(request.url)

                connection = get_db_connection()
                if connection is None:
                    flash("Database connection failed.", "error")
                    return redirect(url_for('pharma.bulk_insert_pharma'))

                cursor = connection.cursor()

                insert_query = f"""
                    INSERT INTO pharmaitemdata (
                        {', '.join([f'`{col}`' for col in required_columns])}
                    ) VALUES ({', '.join(['%s'] * len(required_columns))})
                """

                cursor.executemany(insert_query, data_tuples)
                connection.commit()

                flash(f"Successfully inserted {len(data_tuples)} records.", "success")
                return redirect(url_for('pharma.bulk_insert_pharma'))

            except Exception as e:
                flash(f"Error: {str(e)}", "error")
                return redirect(url_for('pharma.bulk_insert_pharma'))

            finally:
                if "cursor" in locals():
                    cursor.close()
                if "connection" in locals():
                    connection.close()

        else:
            flash("Invalid file type. Please upload an Excel file (.xls or .xlsx).", "error")
            return redirect(request.url)

    # GET request renders the bulk insert template
    return render_template("bulk_insert.html")

@pharma_routes.route("/download_template")
def download_pharma_template():
    columns = [
        "FINANCIAL_YEAR","RC_EFFECTIVE_DATE_FROM","END_DATE","TYPE","FORMULATION","MFG","ARC_No","ITEM_CODE",
        "DESCRIPTION","PACK_SIZE","PUOM","DENOMINATOR","NUMERATOR","BUOM","GST_PERCENT","PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY)",
        "PURCHASE_PACK_PRICE_WITHOUT_TAX_FOR_(FY)","PURCHASE_MRP_PER_UNIT_WITHOUT_TAX_FOR_(FY)","PURCHASE_PACK_MRP_WITHOUT_TAX_FOR_(FY)",
        "OFFERS","CATEGORY","HSN_NO","MHB1","MMB1","MWP1","MNB1","KMC1","MDP1","MGA1","MJP1","MSA1","MVJ1","MHSR","MHVR","MHPK","MHPB",
        "MHYP","MHHB","MHDB","MHMY","MHGG","MHP1","MHGH","MHSL","MDHK","MSLA","MBBS","MMKA","MHKM","MEST","MPPP","MHNB","MHSB","MHMR",
        "MHRA","MHRN","MHSG","MHRP","MHEC","CM_TEAM_HEAD"
    ]

    df = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='pharma_bulk_insert')
    output.seek(0)

    return send_file(output, download_name="pharma_template.xlsx", as_attachment=True) 


 


@pharma_routes.route('/update', methods=['GET', 'POST'])
def pharma_update_item():
    if request.method == 'POST':
        item_code = request.form.get("item_code", "").strip()
        new_mrp_pharma = request.form.get("new_mrp_pharma", "").strip()
        new_price_pharma = request.form.get("new_price_pharma", "").strip()

        if not item_code or not new_mrp_pharma or not new_price_pharma:
            flash(" All fields are required!", "danger")
            return redirect(url_for('pharma.pharma_update_item'))
        try:
            connection = get_db_connection()
            if connection is None:
                flash(" Failed to connect to database.", "danger")
                return redirect(url_for('pharma.pharma_update_item'))
            with connection.cursor() as cursor:
                query = """
                    UPDATE pharmaitemdata 
                    SET 
                        `PURCHASE_PACK_MRP_WITHOUT_TAX_FOR_(FY)` = %s,
                        `PURCHASE_PACK_PRICE_WITHOUT_TAX_FOR_(FY)` = %s
                    WHERE ITEM_CODE = %s
                """
                cursor.execute(query, (new_mrp_pharma, new_price_pharma, item_code))
                rows_updated = cursor.rowcount

            connection.commit()

            if rows_updated == 0:
                flash("⚠️ No matching item code found. No changes were made.", "warning")
            else:
                flash(" Pharma item updated successfully!", "success")

            return redirect(url_for('pharma.pharma_update_item'))

        except Exception as e:
            if connection:
                connection.rollback()
            flash(f" Error updating pharma item: {str(e)}", "danger")
            return redirect(url_for('pharma.pharma_update_item'))
        finally:
            if connection:
                connection.close()

    return render_template('update.html')


@pharma_routes.route("/delete", methods=["GET", "POST"])
def delete_pharma_item():
    if request.method == "GET":
        return render_template("delete.html")  

    mfg_name = request.form.get("mfg_name", "").strip()
    if not mfg_name:
        flash(" MFG name cannot be empty.", "danger")
        return redirect(url_for("pharma.delete_pharma_item"))

    connection = get_db_connection()
    if connection is None:
        flash(" Failed to connect to database.", "danger")
        return redirect(url_for("pharma.index"))

    cursor = connection.cursor()
    try:
        delete_query = "DELETE FROM pharmaitemdata WHERE MFG = %s"
        cursor.execute(delete_query, (mfg_name,))
        rows_deleted = cursor.rowcount
        connection.commit()

        if rows_deleted > 0:
            flash(f" Successfully deleted {rows_deleted} record(s) for MFG '{mfg_name}'.", "success")
        else:
            flash(f" No records found for MFG '{mfg_name}'.", "warning")

    except pymysql.MySQLError as e:
        flash(f" Error deleting data: {e}", "danger")

    finally:
        connection.close()

    return redirect(url_for("pharma.delete_pharma_item"))

@pharma_routes.route('/search_info', methods=['GET', 'POST'])
def search_info():
    if request.method == 'POST':
        item_codes = (request.form.get("item_codes") or "").strip()
        manufacturer_name = (request.form.get("manufacturer_name") or "").strip()
        unit_names = request.form.getlist("unit_name[]")

        if not unit_names or (not item_codes and not manufacturer_name):
            flash("❌ Please enter Item Code(s) or Manufacturer Name, and select at least one Unit Name!", "warning")
            return redirect(url_for('pharma.search_info'))

        connection = get_db_connection()
        if connection is None:
            flash("❌ Database connection failed!", "danger")
            return redirect(url_for('pharma.search_info'))

        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SHOW COLUMNS FROM pharmaitemdata")
        existing_columns = {row["Field"] for row in cursor.fetchall()}

        price_column = "PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY)"
        if price_column not in existing_columns:
            flash(f"❌ Price column '{price_column}' does not exist in database!", "danger")
            return redirect(url_for('pharma.search_info'))

        all_results = []
        item_code_list = []
        if item_codes:
            import re
            item_code_list = re.split(r'[\s,]+', item_codes.strip())
            item_code_list = [code.strip() for code in item_code_list if code.strip()]

        for unit in unit_names:
            if unit not in existing_columns:
                flash(f"❌ Unit column '{unit}' does not exist!", "warning")
                continue

            selected_columns = [
                f"`{unit}` AS Vendor",
                "ITEM_CODE AS `Item Code`",
                "0 AS Purchase_org",
                f"'{unit}' AS Unit_name",
                "0 AS Standard",
                "0 AS Consignment",
                "5 AS `Plan Deliver Time`",
                "0 AS `Purchase_group`",
                "0 AS `Standard Qty`",
                "0 AS `Tax code`",
                "0 AS `Pr. Date Cat.`",
                f"`{price_column}` AS Purchase_price",
                "RC_EFFECTIVE_DATE_FROM",
                "END_DATE",
                "MFG"
            ]

            query = f"SELECT {', '.join(selected_columns)} FROM pharmaitemdata WHERE 1=1"
            query_params = []

            if item_code_list:
                placeholders = ', '.join(['%s'] * len(item_code_list))
                query += f" AND ITEM_CODE IN ({placeholders})"
                query_params.extend(item_code_list)

            if manufacturer_name:
                query += " AND MFG LIKE %s"
                query_params.append(f"%{manufacturer_name}%")

            cursor.execute(query, query_params)
            unit_results = cursor.fetchall()
            if unit_results:
                all_results.extend(unit_results)

        connection.close()

        if not all_results:
            flash("⚠️ No records found for the given criteria.", "info")
            return redirect(url_for('pharma.search_info'))

        session['search_results'] = all_results
        session['column_order'] = list(all_results[0].keys()) if all_results else []
        return render_template('search_info_results.html', results=all_results, unit_name=", ".join(unit_names))

    return render_template('search_info.html')
 

@pharma_routes.route('/export_results', methods=['POST'])
def export_results():
    results = session.get('search_results', [])
    column_order = session.get('column_order', [])

    if not results:
        flash(" No data available for export!", "warning")
        return redirect(url_for('pharma.search_info'))

    df = pd.DataFrame(results)

    if column_order:
        column_order = [col for col in column_order if col in df.columns]
        df = df[column_order]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="SearchResults")

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=search_results.xlsx"}
    )

@pharma_routes.route('/view_all')
def view_all():
    connection = None
    pharma_items = []

    try:
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for('pharma.index'))

        # Use DictCursor for dictionary-style rows
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch only Pharma items
            cursor.execute("SELECT * FROM pharmaitemdata")
            pharma_items = cursor.fetchall() or []
            pharma_items = list(pharma_items)

    except pymysql.MySQLError as e:
        flash(f"Database Error: {e}", "danger")
    finally:
        if connection:
            connection.close()

    # Render only Pharma items
    return render_template('view_all.html', pharma_items=pharma_items)


# ================================
# UPDATE PHARMA ITEM ONLY
# ================================
@pharma_routes.route('/update_item_all_item', methods=['POST'])
def update_item_all_item():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"message": "Invalid JSON payload"}), 400

    description = data.get('description')
    updates = data.get('data')

    if not description or not updates:
        return jsonify({"message": "Missing DESCRIPTION or update data"}), 400

    set_clause = ", ".join(f"`{key}` = %s" for key in updates.keys())
    values = list(updates.values())

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"""
                UPDATE `pharmaitemdata`
                SET {set_clause}
                WHERE `DESCRIPTION` = %s
            """
            values.append(description)
            cursor.execute(sql, values)
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({"message": "No matching Pharma item found with that DESCRIPTION."}), 404

        return jsonify({"message": "Pharma item updated successfully!"}), 200

    except pymysql.MySQLError as e:
        return jsonify({"message": f"Database error: {e}"}), 500
    finally:
        if connection:
            connection.close()



 