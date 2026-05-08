import streamlit as st
import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(
        database="Sales_Management_System",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432"
    )

st.set_page_config(page_title="Sales Dashboard", layout="wide")
st.title("Sales Dashboard")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'branch_id' not in st.session_state:
    st.session_state.branch_id = None

if not st.session_state.logged_in:
    st.subheader("Login")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT role, branch_id FROM users WHERE username=%s AND password=%s",
                (username, password)
            )
            user = cur.fetchone()
            conn.close()
            if user:
                st.session_state.logged_in = True
                st.session_state.role = user[0]
                st.session_state.branch_id = user[1]
                st.rerun()
            else:
                st.error("Invalid credentials")
else:
    st.sidebar.header(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    conn = get_connection()

    if st.session_state.role == 'Super Admin':
        query = """
        SELECT cs.*, b.branch_name
        FROM customer_sales cs
        JOIN branches b ON cs.branch_id = b.branch_id
        ORDER BY cs.sale_id
        """
    else:
        query = f"""
        SELECT cs.*, b.branch_name
        FROM customer_sales cs
        JOIN branches b ON cs.branch_id = b.branch_id
        WHERE cs.branch_id = {st.session_state.branch_id}
        ORDER BY cs.sale_id
        """

    df = pd.read_sql(query, conn)

    df['date'] = pd.to_datetime(df['date'])
    df['pending_amount'] = df['gross_sales'] - df['received_amount']

    st.sidebar.subheader("Filters")

    if st.session_state.role == 'Super Admin':
        branches = df['branch_name'].unique()
        selected_branch = st.sidebar.multiselect("Branch", branches)
    else:
        selected_branch = None

    products = df['product_name'].unique()
    selected_product = st.sidebar.multiselect("Product", products)

    from_date = st.sidebar.date_input("From Date", value=None)
    to_date = st.sidebar.date_input("To Date", value=None)

    filtered_df = df.copy()

    if selected_branch:
        filtered_df = filtered_df[filtered_df['branch_name'].isin(selected_branch)]

    if selected_product:
        filtered_df = filtered_df[filtered_df['product_name'].isin(selected_product)]

    if from_date and to_date:
        filtered_df = filtered_df[
            (filtered_df['date'].dt.date >= from_date) &
            (filtered_df['date'].dt.date <= to_date)
        ]

    st.subheader("Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", f"₹{filtered_df['gross_sales'].sum():,.2f}")
    col2.metric("Received", f"₹{filtered_df['received_amount'].sum():,.2f}")
    col3.metric("Pending", f"₹{filtered_df['pending_amount'].sum():,.2f}")

    st.dataframe(filtered_df, use_container_width=True)

    st.write("---")
    st.subheader("Frequently asked questions")

    if st.session_state.role == 'Super Admin':
        branch_filter_cs = ""
    else:
        bid = st.session_state.branch_id
        branch_filter_cs = f" WHERE cs.branch_id = {bid}"

    question = st.selectbox("Select a Question", [
        "Select...",
        "Monthly summary",
        "Top Customers",
        "Pending Payments"
    ])

    if question == "Monthly summary":
        result_df = pd.read_sql(f"""
            SELECT DATE_TRUNC('month', date) AS month,
                   SUM(gross_sales) AS total_sales,
                   SUM(received_amount) AS total_received
            FROM customer_sales cs
            {branch_filter_cs}
            GROUP BY 1
            ORDER BY 1
        """, conn)
        st.dataframe(result_df, use_container_width=True)

    elif question == "Top Customers":
        result_df = pd.read_sql(f"""
            SELECT name,
                   SUM(gross_sales) AS total_sales
            FROM customer_sales cs
            {branch_filter_cs}
            GROUP BY name
            ORDER BY total_sales DESC
            LIMIT 5
        """, conn)
        st.dataframe(result_df, use_container_width=True)

    elif question == "Pending Payments":
        result_df = pd.read_sql(f"""
            SELECT sale_id, name, gross_sales, received_amount,
                   (gross_sales - received_amount) AS pending
            FROM customer_sales cs
            {branch_filter_cs}
            WHERE received_amount < gross_sales
            ORDER BY pending DESC
        """, conn)
        st.dataframe(result_df, use_container_width=True)

    if st.session_state.role in ['Super Admin', 'Admin']:
        st.write("---")
        st.subheader("Manual Entry")

        tab1, tab2 = st.tabs(["Add Sale", "Add Payment"])

        with tab1:
            with st.form("sale_form"):
                sale_id = st.number_input("Sale ID", step=1)
                name = st.text_input("Customer Name")
                mobile = st.text_input("Mobile Number")
                product = st.selectbox("Product", ["DS", "DA", "BA", "FSD"])
                amount = st.number_input("Gross Amount", min_value=0.0)

                if st.session_state.role == 'Super Admin':
                    branch_id = st.selectbox("Branch ID", df['branch_id'].unique())
                else:
                    branch_id = st.session_state.branch_id
                    st.write(f"Branch ID: {branch_id}")

                if st.form_submit_button("Add Sale"):
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO customer_sales
                        (sale_id, branch_id, date, name, mobile_number, product_name, gross_sales, received_amount, status)
                        VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, 0, 'Open')
                    """, (sale_id, branch_id, name, mobile, product, amount))
                    conn.commit()
                    st.success("Sale Added")
                    st.rerun()

        with tab2:
            with st.form("payment_form"):
                sale_list = filtered_df['sale_id'].tolist()
                sale_id = st.selectbox("Select Sale_ID", sale_list)
                amount = st.number_input("Amount Paid", min_value=0.0)
                method = st.selectbox("Method", ["Cash", "UPI", "Card", "Bank Transfer"])

                if st.form_submit_button("Add Payment"):
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            SELECT gross_sales, received_amount
                            FROM customer_sales
                            WHERE sale_id = %s
                        """, (sale_id,))
                        result = cur.fetchone()

                        if not result:
                            st.error("Sale not found")
                        else:
                            gross, received = result
                            gross = float(gross)
                            received = float(received)
                            amount = float(amount)
                            new_total = received + amount

                            if new_total > gross:
                                st.error(f"Payment exceeds limit! Pending: ₹{gross - received:.2f}")
                            else:
                                cur.execute("""
                                    INSERT INTO payment_splits
                                    (sale_id, payment_date, amount_paid, payment_method)
                                    VALUES (%s, CURRENT_DATE, %s, %s)
                                """, (sale_id, amount, method))

                                cur.execute("""
                                    UPDATE customer_sales
                                    SET received_amount = %s
                                    WHERE sale_id = %s
                                """, (new_total, sale_id))

                                status = "Closed" if new_total == gross else "Open"

                                cur.execute("""
                                    UPDATE customer_sales
                                    SET status = %s
                                    WHERE sale_id = %s
                                """, (status, sale_id))

                                conn.commit()
                                st.success("Payment Added")
                                st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error: {e}")

    conn.close()
