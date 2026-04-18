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
            (filtered_df['sale_date'].dt.date >= from_date) &
            (filtered_df['sale_date'].dt.date <= to_date)
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
        branch_filter_join = ""
        extra_condition = ""
    else:
        bid = st.session_state.branch_id
        branch_filter_cs = f" WHERE cs.branch_id = {bid}"
        branch_filter_join = f" WHERE cs.branch_id = {bid}"
        extra_condition = f" AND cs.branch_id = {bid}"

    question = st.selectbox("Select a Question", [
        "Select...",
        "1. All customer sales",
        "2. All branches",
        "3. All payments",
        "4. Open sales",
        "5. Sales from Chennai branch",
        "6. Total gross sales",
        "7. Total received amount",
        "8. Total pending amount",
        "9. Count sales per branch",
        "10. Average gross sales",
        "11. Sales with branch name",
        "12. Sales with total payment",
        "13. Branch-wise total sales",
        "14. Sales with payment method",
        "15. Sales with branch admin",
        "16. Pending > 5000",
        "17. Top 3 sales",
        "18. Highest sales branch",
        "19. Monthly summary",
        "20. Payment method summary"
    ])

    if question != "Select...":

        query_map = {

            "1. All customer sales": f"SELECT * FROM customer_sales cs {branch_filter_cs}",

            "2. All branches": "SELECT * FROM branches",

            "3. All payments": f"""
                SELECT ps.*
                FROM payment_splits ps
                JOIN customer_sales cs ON ps.sale_id = cs.sale_id
                {branch_filter_join}
            """,

            "4. Open sales": f"""
                SELECT * FROM customer_sales cs
                WHERE status='Open'
                {extra_condition}
            """,

            "5. Sales from Chennai branch": f"""
                SELECT cs.*
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                WHERE b.branch_name = 'Chennai'
                {extra_condition}
            """,

            "6. Total gross sales": f"SELECT SUM(gross_sales) FROM customer_sales cs {branch_filter_cs}",

            "7. Total received amount": f"SELECT SUM(received_amount) FROM customer_sales cs {branch_filter_cs}",

            "8. Total pending amount": f"""
                SELECT SUM(gross_sales - received_amount)
                FROM customer_sales cs
                {branch_filter_cs}
            """,

            "9. Count sales per branch": f"""
                SELECT branch_id, COUNT(*) 
                FROM customer_sales cs
                {branch_filter_cs}
                GROUP BY branch_id
            """,

            "10. Average gross sales": f"""
                SELECT AVG(gross_sales)
                FROM customer_sales cs
                {branch_filter_cs}
            """,

            "11. Sales with branch name": f"""
                SELECT cs.*, b.branch_name
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                {branch_filter_join}
            """,

            "12. Sales with total payment": f"""
                SELECT cs.sale_id, cs.name, SUM(ps.amount_paid) AS total_paid
                FROM customer_sales cs
                LEFT JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                {branch_filter_join}
                GROUP BY cs.sale_id, cs.name
            """,

            "13. Branch-wise total sales": f"""
                SELECT b.branch_name, SUM(cs.gross_sales)
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                {branch_filter_join}
                GROUP BY b.branch_name
            """,

            "14. Sales with payment method": f"""
                SELECT cs.sale_id, ps.payment_method
                FROM customer_sales cs
                JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                {branch_filter_join}
            """,

            "15. Sales with branch admin": f"""
                SELECT cs.*, b.branch_admin_name
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                {branch_filter_join}
            """,

            "16. Pending > 5000": f"""
                SELECT *, (gross_sales - received_amount) AS pending
                FROM customer_sales cs
                WHERE (gross_sales - received_amount) > 5000
                {extra_condition}
            """,

            "17. Top 3 sales": f"""
                SELECT *
                FROM customer_sales cs
                {branch_filter_cs}
                ORDER BY gross_sales DESC
                LIMIT 3
            """,

            "18. Highest sales branch": f"""
                SELECT b.branch_name, SUM(cs.gross_sales) AS total
                FROM customer_sales cs
                JOIN branches b ON cs.branch_id = b.branch_id
                {branch_filter_join}
                GROUP BY b.branch_name
                ORDER BY total DESC
                LIMIT 1
            """,

            "19. Monthly summary": f"""
                SELECT DATE_TRUNC('month', sale_date), SUM(gross_sales)
                FROM customer_sales cs
                {branch_filter_cs}
                GROUP BY 1
                ORDER BY 1
            """,

            "20. Payment method summary": f"""
                SELECT ps.payment_method, SUM(ps.amount_paid)
                FROM payment_splits ps
                JOIN customer_sales cs ON ps.sale_id = cs.sale_id
                {branch_filter_join}
                GROUP BY ps.payment_method
            """
        }

        result_df = pd.read_sql(query_map[question], conn)
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
                        (sale_id, branch_id, sale_date, name, mobile_number, product_name, gross_sales, received_amount, status)
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
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO payment_splits
                        (sale_id, payment_date, amount_paid, payment_method)
                        VALUES (%s, CURRENT_DATE, %s, %s)
                    """, (sale_id, amount, method))

                    conn.commit()
                    st.success("Payment Added")
                    st.rerun()

    conn.close()