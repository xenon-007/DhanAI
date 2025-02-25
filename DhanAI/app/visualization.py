import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

def shorten_label(label, max_length=20):
    """
    Shortens long category descriptions to improve readability.
    """
    return label if len(label) <= max_length else label[:max_length] + "..."

def plot_spending_chart(df):

    
    if df.empty:
        st.warning("No transactions available for visualization.")
        return

   
    plt.style.use("dark_background")
    sns.set_palette("magma")  
    sns.set_style("dark")

    
    st.subheader("📊 Spending by Category")
    category_spending = df[df["transaction_type"] == "Expense"].groupby("description")["amount"].sum().sort_values(ascending=False)

    if not category_spending.empty:
        top_categories = category_spending[:10]  
        category_labels = [shorten_label(label) for label in top_categories.index]  

        fig, ax = plt.subplots(figsize=(5, 2.5))  
        sns.barplot(x=top_categories.values, y=category_labels, ax=ax, palette="coolwarm")
        
        ax.set_xlabel("Total Amount (₹)", color="white")
        ax.set_ylabel("Category", color="white")
        ax.set_title("Top 10 Spending Categories", color="white")
        ax.tick_params(colors="white")

        st.pyplot(fig)
    else:
        st.warning("No expense data available for category breakdown.")

    
    st.subheader("💰 Income vs Expense")
    income_expense = df.groupby("transaction_type")["amount"].sum()

    if not income_expense.empty:
        fig, ax = plt.subplots(figsize=(5, 2.5))
        income_expense.plot(kind="bar", color=["green", "red"], ax=ax)

        ax.set_ylabel("Total Amount (₹)", color="white")
        ax.set_title("Income vs Expenses", color="white")
        ax.set_xticklabels(["Expense", "Income"], rotation=0, color="white")
        ax.tick_params(colors="white")

        st.pyplot(fig)
    else:
        st.warning("No sufficient data for income vs expense comparison.")
