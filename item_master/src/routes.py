import datetime
import io
import math
import re
from flask import Blueprint, Response, render_template, request, redirect, flash, jsonify, send_file, session
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



app_routes = Blueprint('app_routes', __name__)

ALLOWED_EXTENSIONS = {"xlsx"}


@app_routes.route('/')
def index():
    return render_template('index.html')

@app_routes.route('/search', methods=['GET', 'POST'])
def search_item():
    if request.method == 'POST':
        item_codes = (request.form.get("item_codes") or "").strip()
        mfg = (request.form.get("mfg") or "").strip()
        vendor_code = (request.form.get("vendor_code") or "").strip()
        description = (request.form.get("description") or "").strip()
        unit_names = request.form.getlist("unit_name[]")

        if not unit_names:
            flash("Please select at least one Unit Name!", "warning")
            return redirect(url_for('app_routes.search_item'))

        if not any([item_codes, mfg, vendor_code, description]):
            flash("Please enter at least one search criterion!", "warning")
            return redirect(url_for('app_routes.search_item'))

        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed!", "danger")
            return redirect(url_for('app_routes.index'))

        cursor = connection.cursor()

        selected_units = ", ".join([f"`{unit}` AS `{unit}`" for unit in unit_names])
        query = f"""
            SELECT `ITEM_CODE`, `HSN_NO`, `DESCRIPTION`, `BRAND`, `PRODUCT_CODE`, `CATEGORY`, `MFG`, 
            `MRP_(FY_CURRENT_YEAR)`, 
            `PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_CURRENT_YEAR)`, 
            `BUOM`, `PACKING`, `PUOM`,{selected_units}
            FROM itemdata
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

        if vendor_code:
            query += f" AND ({' OR '.join([f'`{unit}` = %s' for unit in unit_names])})"
            params.extend([vendor_code] * len(unit_names))

        if description:
            query += " AND `DESCRIPTION` LIKE %s"
            params.append(f"%{description}%")

        cursor.execute(query, params)
        results = cursor.fetchall()
        connection.close()

        if not results:
            flash("No records found matching your search criteria.", "info")
            return redirect(url_for('app_routes.search_item'))

        session['search_results'] = results
        session['column_order'] = list(results[0].keys())
        return render_template('search_results.html', results=results, source='gc')
       #return render_template('search_results.html', results=results)

    return render_template('search.html')

 


@app_routes.route('/search_info', methods=['GET', 'POST'])
def search_info():
    if request.method == 'POST':
        item_codes = (request.form.get("item_codes") or "").strip()
        manufacturer_name = (request.form.get("manufacturer_name") or "").strip()
        unit_names = request.form.getlist("unit_name[]")

        if not unit_names or (not item_codes and not manufacturer_name):
            flash("❌ Please enter Item Code(s) or Manufacturer Name, and select at least one Unit Name!", "warning")
            return redirect(url_for('app_routes.search_info'))

        connection = get_db_connection()
        if connection is None:
            flash("❌ Database connection failed!", "danger")
            return redirect(url_for('app_routes.index'))

        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Get available DB columns
        cursor.execute("SHOW COLUMNS FROM itemdata")
        existing_columns = {row["Field"] for row in cursor.fetchall()}

        price_column = "PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_CURRENT_YEAR)"
        if price_column not in existing_columns:
            flash(f"❌ Price column '{price_column}' does not exist in database!", "danger")
            return redirect(url_for('app_routes.search_info'))

        all_results = []

        # Clean and split item codes (handle space or comma separated)
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

           
            query = f"""
                SELECT {', '.join(selected_columns)}
                FROM itemdata
                WHERE 1 = 1
                """
            query_params = []
            
            filters = []
            if item_code_list:
                placeholders = ', '.join(['%s'] * len(item_code_list))
                query += f" AND ITEM_CODE IN ({placeholders})"
                query_params.extend(item_code_list)

            if manufacturer_name:
                query += " AND MFG LIKE %s"
                query_params.append(f"%{manufacturer_name}%")

            if filters:
                query += " AND " + " AND ".join(filters)

            # Debug logs (optional)
            # print("Executing Query:", query)
            # print("With Parameters:", query_params)

            cursor.execute(query, query_params)
            unit_results = cursor.fetchall()

            if unit_results:
                all_results.extend(unit_results)

        connection.close()

        if not all_results:
            flash("⚠️ No records found for the given criteria.", "info")
            return redirect(url_for('app_routes.search_info'))

        # Save to session for download
        session['search_results'] = all_results
        session['column_order'] = list(all_results[0].keys()) if all_results else []

        return render_template(
            'search_info_results.html',
            results=all_results,
            unit_name=", ".join(unit_names)
        )

    # If GET request
    return render_template('search_info.html')


@app_routes.route('/export_results', methods=['POST'])
def export_results():
    results = session.get('search_results', [])
    column_order = session.get('column_order', [])

    if not results:
        flash("⚠️ No data available for export!", "warning")
        return redirect(url_for('app_routes.search_info'))

    df = pd.DataFrame(results)

    # Clean and reorder safely
    if column_order:
        missing_cols = [col for col in column_order if col not in df.columns]
        if missing_cols:
            print("Missing columns in DataFrame:", missing_cols)
        column_order = [col for col in column_order if col in df.columns]
        df = df[column_order]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="SearchResults")

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=search_results.xlsx"
        }
    )
 

 
@app_routes.route('/insert', methods=['GET', 'POST'])
def insert_item():
    if request.method == 'POST':
        data = request.form.to_dict()

        # ✅ Format specific date fields before inserting
        for date_field in ['RC_EFFECTIVE_DATE_FROM', 'END_DATE']:
            if date_field in data and data[date_field]:
                try:
                    parsed_date = pd.to_datetime(data[date_field], errors='coerce')
                    if pd.notna(parsed_date):
                        data[date_field] = parsed_date.strftime('%d-%m-%Y')
                    else:
                        data[date_field] = None
                except Exception as e:
                    data[date_field] = None  # Default to None if any error occurs

        try:
            connection = get_db_connection()
            if connection is None:
                return redirect(url_for('index'))  # Redirect if connection fails
            cursor = connection.cursor()

            columns = ", ".join([f"`{col}`" for col in data.keys()])
            placeholders = ", ".join(["%s"] * len(data))
            values = tuple(data.values())

            query = f"INSERT INTO itemdata ({columns}) VALUES ({placeholders})"

            cursor.execute(query, values)
            connection.commit()
            flash("Item inserted successfully!", "success")
            return jsonify({'message': 'Item inserted successfully'}), 200

        except pymysql.MySQLError as e:
            connection.rollback()
            flash(f"Database Error: {str(e)}", "danger")
            return jsonify({'error': str(e)}), 400

        finally:
            cursor.close()
            connection.close()

    return render_template('insert.html')



@app_routes.route("/bulk_insert", methods=["GET", "POST"])
def bulk_insert():
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
            filepath = os.path.join("uploads", filename)
            file.save(filepath)

            try:
                # ✅ Read Excel file
                df = pd.read_excel(filepath, dtype=str)
                df.dropna(how="all", inplace=True)

                # ✅ Clean column names
                df.columns = [col.strip() for col in df.columns]

                # ✅ Strip strings
                df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

                # ✅ Replace empty strings and NaN with None
                df.replace('', None, inplace=True)
                df = df.where(pd.notna(df), None)

                # ✅ Required columns
                required_columns = [
                    "FINANCIAL_YEAR", "RC_EFFECTIVE_DATE_FROM", "END_DATE", "TYPE", "MFG", "ITEM_CODE", "ARC_No",
                    "DESCRIPTION", "BUOM", "PUOM", "PACKING", "BRAND", "PRODUCT_CODE", "HSN_NO", "MRP_(FY_PREVIOUS_YEAR)",
                    "PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_PREVIOUS_YEAR)", "MRP_(FY_CURRENT_YEAR)",
                    "PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_CURRENT_YEAR)", "CATEGORY",
                    "MHB1", "MMB1", "MWP1", "MNB1", "KMC1", "MDP1", "MGA1", "MJP1", "MSA1", "MVJ1", "MHSR", "MHVR",
                    "MHPK", "MHPB", "MHYP", "MHHB", "MHDB", "MHMY", "MHGG", "MHP1", "MHGH", "MHSL", "MDHK",
                    "MSLA", "MBBS", "MMKA", "MHKM", "MEST", "MPPP", "MHNB", "MHSB", "MHMR", "MHRA", "MHRN", "MHSG", "MHRP", "MHEC", "CM_TEAM_HEAD"
                ]

                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f"Missing columns in file: {', '.join(missing_columns)}", "error")
                    return redirect(request.url)

                # ✅ Format dates
                for date_col in ['RC_EFFECTIVE_DATE_FROM', 'END_DATE']:
                    if date_col in df.columns:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%d-%m-%Y')
                        df[date_col] = df[date_col].where(pd.notna(df[date_col]), None)
 
                # ✅ Final sanitize before DB insert
                def sanitize_row(row):
                    return tuple(None if (x is None or (isinstance(x, float) and math.isnan(x))) else x for x in row)

                data_tuples = df[required_columns].apply(sanitize_row, axis=1).tolist()

                if not data_tuples:
                    flash("No valid data to insert.", "error")
                    return redirect(request.url)

                # ✅ DB insert
                connection = get_db_connection()
                if connection is None:
                    flash("Database connection failed.", "error")
                    return redirect(url_for('app_routes.index'))

                cursor = connection.cursor()

                insert_query = f"""
                    INSERT INTO itemdata (
                        {', '.join([f'`{col}`' for col in required_columns])}
                    ) VALUES ({', '.join(['%s'] * len(required_columns))})
                """

                cursor.executemany(insert_query, data_tuples)
                connection.commit()

                flash(f"Successfully inserted {len(data_tuples)} records.", "success")
                return redirect(url_for('app_routes.bulk_insert'))

            except Exception as e:
                flash(f"Error: {str(e)}", "error")
                return redirect(url_for('app_routes.bulk_insert'))

            finally:
                if "cursor" in locals():
                    cursor.close()
                if "connection" in locals():
                    connection.close()

    return render_template("bulk_insert.html")

@app_routes.route("/download_template")
def download_template():
    from io import BytesIO
    from flask import send_file
    import pandas as pd

    columns = [
        "FINANCIAL_YEAR", "RC_EFFECTIVE_DATE_FROM", "END_DATE", "TYPE", "MFG", "ITEM_CODE", "ARC_No",
        "DESCRIPTION", "BUOM", "PUOM", "PACKING", "BRAND", "PRODUCT_CODE", "HSN_NO", "MRP_(FY_PREVIOUS_YEAR)",
        "PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_PREVIOUS_YEAR)", "MRP_(FY_CURRENT_YEAR)",
        "PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_CURRENT_YEAR)", "CATEGORY",
        "MHB1", "MMB1", "MWP1", "MNB1", "KMC1", "MDP1", "MGA1", "MJP1", "MSA1", "MVJ1", "MHSR", "MHVR",
        "MHPK", "MHPB", "MHYP", "MHHB", "MHDB", "MHMY", "MHGG", "MHP1", "MHGH", "MHSL", "MDHK",
        "MSLA", "MBBS", "MMKA", "MHKM", "MEST", "MPPP", "MHNB", "MHSB", "MHMR", "MHRA", "MHRN", "MHSG", "MHRP", "MHEC", "CM_TEAM_HEAD"
    ]

    df = pd.DataFrame(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='itemdata_data_bulk insert')
    output.seek(0)

    return send_file(output, download_name="itemdata_template.xlsx", as_attachment=True)


# code 1
@app_routes.route("/delete", methods=["GET", "POST"])
def delete_item():
    if request.method == "GET":
        return render_template("delete.html")

    mfg_name = request.form.get("mfg_name", "").strip()
    if not mfg_name:
        flash(" MFG name cannot be empty.", "danger")
        return redirect(url_for("app_routes.delete_item"))  # Redirects back to the same page

    connection = get_db_connection()
    if connection is None:
        return redirect(url_for("app_routes.index"))  # Redirect if connection fails
    
    cursor = connection.cursor()
    try:
        delete_query = "DELETE FROM itemdata WHERE MFG = %s"
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
    return redirect(url_for("app_routes.delete_item"))  



 

@app_routes.route('/update', methods=['GET', 'POST'])
def update_item():
    if request.method == 'POST':
        item_code = request.form.get("item_code", "").strip()
        new_mrp = request.form.get("new_mrp", "").strip()
        new_price = request.form.get("new_price", "").strip()

        if not item_code or not new_mrp or not new_price:
            flash(" All fields are required!", "danger")
            return redirect(url_for('app_routes.update_item'))

        try:
            connection = get_db_connection()
            if connection is None:
                flash(" Failed to connect to database.", "danger")
                return redirect(url_for('app_routes.update_item'))

            with connection.cursor() as cursor:
                query = """
                    UPDATE itemdata 
                    SET 
                        `MRP_(FY_CURRENT_YEAR)` = %s,
                        `PURCHASE_PRICE_PER_UNIT_WITHOUT_TAX_FOR_(FY_CURRENT_YEAR)` = %s
                    WHERE `ITEM_CODE` = %s
                """
                cursor.execute(query, (new_mrp, new_price, item_code))
                rows_updated = cursor.rowcount

            connection.commit()

            if rows_updated == 0:
                flash(" No matching item code found. No changes were made.", "warning")
            else:
                flash(" Item updated successfully!", "success")

            return redirect(url_for('app_routes.update_item'))

        except Exception as e:
            if connection:
                connection.rollback()
            flash(f" Error updating item: {str(e)}", "danger")
            return redirect(url_for('app_routes.update_item'))

        finally:
            if connection:
                connection.close()

    return render_template('update.html')


@app_routes.route('/download_excel')
def download_excel():
    data_type = request.args.get('type', 'gc')  # default to GC

    try:
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed", "danger")
            return redirect(url_for('app_routes.view_all'))

        cursor = connection.cursor(pymysql.cursors.DictCursor)

        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')

        if data_type == "gc":
            cursor.execute("SELECT * FROM itemdata")
            gc_items = cursor.fetchall()
            df_gc = pd.DataFrame(gc_items)
            df_gc.to_excel(writer, index=False, sheet_name="GC_Data")
            filename = "gc_data.xlsx"

        elif data_type == "pharma":
            cursor.execute("SELECT * FROM pharmaitemdata")
            pharma_items = cursor.fetchall()
            df_pharma = pd.DataFrame(pharma_items)
            df_pharma.to_excel(writer, index=False, sheet_name="Pharma_Data")
            filename = "pharma_data.xlsx"

        writer.close()
        output.seek(0)

        return send_file(output,
                         as_attachment=True,
                         download_name=filename,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except pymysql.MySQLError as e:
        flash(f"Database Error: {e}", "danger")
        return redirect(url_for('app_routes.view_all'))




@app_routes.route('/view_all')
def view_all():
    connection = None
    gc_items = []
    pharma_items = []

    try:
        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for('app_routes.index'))

        # Use DictCursor for dictionary-style rows
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch GC items
            cursor.execute("SELECT * FROM itemdata")
            gc_items = cursor.fetchall() or []
            # Ensure it's a list
            gc_items = list(gc_items)

            # Fetch Pharma items
            cursor.execute("SELECT * FROM pharmaitemdata")
            pharma_items = cursor.fetchall() or []
            pharma_items = list(pharma_items)

    except pymysql.MySQLError as e:
        flash(f"Database Error: {e}", "danger")
    finally:
        if connection:
            connection.close()

    # Always return safe lists, even if empty
    return render_template('view_all.html', items=gc_items, pharma_items=pharma_items)


# ================================
# UPDATE ITEM IN EITHER TABLE
# ================================
@app_routes.route('/update_item_all_item', methods=['POST'])
def update_item_all_item():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"message": "Invalid JSON payload"}), 400

    item_type = data.get('type')
    description = data.get('description')
    updates = data.get('data')

    if not description or not updates:
        return jsonify({"message": "Missing DESCRIPTION or update data"}), 400

    table = 'pharmaitemdata' if item_type == 'pharma' else 'itemdata'
    set_clause = ", ".join(f"`{key}` = %s" for key in updates.keys())
    values = list(updates.values())

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"""
                UPDATE `{table}`
                SET {set_clause}
                WHERE `DESCRIPTION` = %s
            """
            values.append(description)
            cursor.execute(sql, values)
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({"message": "No matching item found with that DESCRIPTION."}), 404

        return jsonify({"message": "Item updated successfully!"}), 200

    except pymysql.MySQLError as e:
        return jsonify({"message": f"Database error: {e}"}), 500
    finally:
        if connection:
            connection.close()