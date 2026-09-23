"""Library of standard IFRS for SME's accounting policy paragraphs (Section 7 / 8.8 of the spec).

Each entry is keyed by the exact policy_area label used on the "Policy Elections"
sheet / PolicyElection.policy_area field. Paragraphs for Sections 17, 11 & 12, 29,
28 and 23 are drawn verbatim from the reference document's pages 11-12; the rest
follow the same drafting register for a generically reusable tool.

`{{n}}` placeholders that need a note number are resolved by the docgen module.
"""

PPE_USEFUL_LIFE_NOTE = (
    "Property, plant and equipment are tangible assets that are held for use in the production or supply of "
    "goods or services, for rental to others or for administrative purposes and are expected to be used during "
    "more than one period.\n\n"
    "Property, plant and equipment is initially measured at cost. Cost includes expenditure that is directly "
    "attributable to the acquisition of the item and, where applicable, the initial estimate of the costs of "
    "dismantling and removing the item and restoring the site on which it is located.\n\n"
    "Property, plant and equipment is subsequently stated at cost less accumulated depreciation and any "
    "accumulated impairment losses.\n\n"
    "Depreciation is provided on all property, plant and equipment to write down the cost, less estimated "
    "residual value, on the straight line basis over the useful life of the asset as follows:\n\n"
    "Item                     Depreciation method     Average useful life\n"
    "{{ppe_useful_life_table}}\n\n"
    "The residual value, useful life and depreciation method of each asset are reviewed at the end of each "
    "reporting period. If the expectations differ from previous estimates, the change is accounted for "
    "prospectively as a change in accounting estimate.\n\n"
    "The company tests for impairment where there is an indication that an asset may be impaired. An "
    "assessment of whether there is an indication of possible impairment is done at each reporting date. Where "
    "the carrying amount of an item of property, plant and equipment is greater than the estimated recoverable "
    "amount, it is written down immediately to its recoverable amount and an impairment loss is charged to "
    "profit or loss.\n\n"
    "An item of property, plant and equipment is derecognised upon disposal or when no future economic "
    "benefits are expected from its continued use or disposal. Any gain or loss arising from the derecognition "
    "of an item of property, plant and equipment, determined as the difference between the net disposal "
    "proceeds, if any, and the carrying amount of the item, is included in profit or loss when the item is "
    "derecognised."
)

FINANCIAL_INSTRUMENTS_NOTE = (
    "Financial instruments at amortised cost are initially measured at the transaction price (including "
    "transaction costs) unless the arrangement constitutes, in effect, a financing transaction, in which case "
    "the instrument is measured at the present value of the future payments discounted at a market rate of "
    "interest.\n\n"
    "Financial instruments at amortised cost are subsequently measured using the effective interest method, "
    "less any impairment. At the end of each reporting period, the carrying amounts of financial assets carried "
    "at amortised cost are reviewed to determine whether there is objective evidence of impairment. If there is "
    "objective evidence, an impairment loss is recognised in profit or loss immediately.\n\n"
    "Trade and other receivables that arise from the company's ordinary course of business are measured at the "
    "undiscounted amount of cash expected to be received, less any impairment, when the effect of discounting "
    "is immaterial.\n\n"
    "Trade and other payables that arise from the company's ordinary course of business are measured at the "
    "undiscounted amount owed, when the effect of discounting is immaterial.\n\n"
    "Loans to and from shareholders/directors are measured, on initial recognition, at the present value of the "
    "expected future cash flows discounted at a market rate of interest for a similar debt instrument, and "
    "subsequently at amortised cost using the effective interest method, unless the loan is repayable on "
    "demand and interest-free/at a market related rate, in which case it is measured at the undiscounted amount "
    "receivable or payable.\n\n"
    "Cash and cash equivalents comprise cash on hand and demand deposits, together with other short-term, "
    "highly liquid investments that are readily convertible to a known amount of cash and are subject to an "
    "insignificant risk of changes in value."
)

TAX_NOTE = (
    "Current tax assets and liabilities for the current and prior periods are measured at the amount expected "
    "to be recovered from, or paid to, the tax authorities, using the tax rates and tax laws that have been "
    "enacted or substantively enacted by the reporting date.\n\n"
    "The company qualifies as a Small Business Corporation as defined in section 12E of the Income Tax Act, and "
    "the applicable graduated tax rates for Small Business Corporations have been applied in determining the "
    "current tax charge, where applicable.\n\n"
    "Deferred tax is not separately recognised in these annual financial statements - see Section 10 (Out of "
    "scope) of the AFS Compiler for the reasoning."
)

EMPLOYEE_BENEFITS_NOTE = (
    "The cost of short-term employee benefits (those payable within 12 months after the service is rendered, "
    "such as paid vacation leave and sick leave, bonuses, and non-monetary benefits such as medical care) are "
    "recognised in the period in which the service is rendered and are not discounted.\n\n"
    "The expected cost of compensated absences is recognised as an expense as the employees render services "
    "that increase their entitlement, in the case of non-accumulating absences, when the absence occurs.\n\n"
    "The expected cost of profit sharing and bonus payments is recognised as an expense when there is a legal "
    "or constructive obligation to make such payments as a result of past performance."
)

REVENUE_NOTE = (
    "Revenue is measured at the fair value of the consideration received or receivable and represents the "
    "amounts receivable for services rendered in the ordinary course of business, net of value added tax.\n\n"
    "Revenue from the rendering of services is recognised by reference to the stage of completion of the "
    "transaction at the reporting date, provided that the outcome of the transaction can be estimated reliably. "
    "The stage of completion is determined by services performed to date as a percentage of total services to "
    "be performed.\n\n"
    "Interest income is recognised, in profit or loss, using the effective interest method."
)

INVENTORIES_NOTE = (
    "Inventories are measured at the lower of cost and estimated selling price less costs to complete and "
    "sell. The cost of inventories is assigned using the first-in, first-out (FIFO) formula. The same cost "
    "formula is used for all inventories having a similar nature and use.\n\n"
    "The cost of inventories comprises all costs of purchase, costs of conversion and other costs incurred in "
    "bringing the inventories to their present location and condition.\n\n"
    "When inventories are sold, the carrying amount of those inventories is recognised as an expense in the "
    "period in which the related revenue is recognised."
)

LEASES_NOTE = (
    "Leases are classified as finance leases whenever the terms of the lease transfer substantially all the "
    "risks and rewards of ownership to the lessee. All other leases are classified as operating leases.\n\n"
    "Payments made under operating leases are recognised in profit or loss on a straight-line basis over the "
    "term of the lease. Lease incentives received are recognised as an integral part of the total lease "
    "expense, over the term of the lease."
)

PROVISIONS_NOTE = (
    "Provisions are recognised when the company has a present legal or constructive obligation as a result of "
    "a past event, it is probable that an outflow of resources embodying economic benefits will be required to "
    "settle the obligation, and a reliable estimate can be made of the amount of the obligation.\n\n"
    "Provisions are measured at the best estimate of the expenditure required to settle the present obligation "
    "at the reporting date.\n\n"
    "A contingent liability is a possible obligation that arises from past events and whose existence will be "
    "confirmed only by the occurrence or non-occurrence of uncertain future events not wholly within the "
    "control of the company, or a present obligation that is not recognised because it is not probable that an "
    "outflow of resources will be required, or the amount cannot be measured reliably. Contingent liabilities "
    "are not recognised but are disclosed unless the possibility of an outflow of resources is remote."
)

RELATED_PARTIES_NOTE = (
    "The company discloses details of transactions with related parties which are not at arm's length or "
    "in the ordinary course of business, or where the terms of the transaction are not consistent with those "
    "currently available in the marketplace. Where a related party transaction has occurred within the ordinary "
    "course of business and on terms and conditions no more or less favourable than those which it is "
    "reasonable to expect the company would have adopted if dealing with that party at arm's length, the "
    "company discloses the nature of the related party relationship as well as the types of transactions "
    "entered into where necessary for an understanding of the potential effect of the relationship on the "
    "financial statements."
)

IMPAIRMENT_NOTE = (
    "At each reporting date the company reviews the carrying amounts of its non-financial assets to determine "
    "whether there is any indication that those assets have suffered an impairment loss. If any such indication "
    "exists, the recoverable amount of the asset is estimated in order to determine the extent of the "
    "impairment loss, if any. Where the carrying amount of an asset exceeds its recoverable amount, the asset "
    "is considered impaired and is written down to its recoverable amount, with the impairment loss recognised "
    "immediately in profit or loss."
)

FOREIGN_CURRENCY_NOTE = (
    "Transactions in currencies other than the company's functional currency (foreign currency transactions) "
    "are recorded initially at the functional currency spot rate of exchange ruling at the date of the "
    "transaction. Monetary assets and liabilities denominated in foreign currencies are translated at the "
    "functional currency spot rate of exchange ruling at the reporting date. All exchange rate differences are "
    "recognised in profit or loss."
)

GOVERNMENT_GRANTS_NOTE = (
    "Government grants are not recognised until there is reasonable assurance that the company will comply "
    "with the conditions attaching to them and that the grants will be received. Grants relating to income are "
    "recognised in profit or loss over the periods necessary to match them with the related costs which they "
    "are intended to compensate, on a systematic basis. Grants relating to assets are recognised in profit or "
    "loss over the expected useful life of the related asset."
)

BORROWING_COSTS_NOTE = (
    "All borrowing costs are recognised as an expense in profit or loss in the period in which they are "
    "incurred, in accordance with the cost model permitted for Small and Medium-sized Entities."
)

CASH_FLOW_NOTE = (
    "Cash flows are reported using the indirect/direct method as applicable, distinguishing between operating, "
    "investing and financing activities. Cash and cash equivalents comprise cash on hand and demand deposits, "
    "and other short-term highly liquid investments that are readily convertible to a known amount of cash and "
    "are subject to an insignificant risk of changes in value."
)

POLICY_LIBRARY: dict[str, dict] = {
    "Property, plant and equipment (Section 17)": {
        "heading": "Property, plant and equipment",
        "body": PPE_USEFUL_LIFE_NOTE,
    },
    "Financial instruments (Sections 11 & 12)": {
        "heading": "Financial instruments",
        "body": FINANCIAL_INSTRUMENTS_NOTE,
    },
    "Income tax, current and deferred (Section 29)": {
        "heading": "Tax",
        "body": TAX_NOTE,
    },
    "Employee benefits, short-term (Section 28)": {
        "heading": "Employee benefits",
        "body": EMPLOYEE_BENEFITS_NOTE,
    },
    "Revenue (Section 23)": {
        "heading": "Revenue",
        "body": REVENUE_NOTE,
    },
    "Inventories (Section 13)": {
        "heading": "Inventories",
        "body": INVENTORIES_NOTE,
    },
    "Leases (Section 20)": {
        "heading": "Leases",
        "body": LEASES_NOTE,
    },
    "Provisions and contingencies (Section 21)": {
        "heading": "Provisions and contingencies",
        "body": PROVISIONS_NOTE,
    },
    "Related party disclosures (Section 33)": {
        "heading": "Related parties",
        "body": RELATED_PARTIES_NOTE,
    },
    "Impairment of assets (Section 27)": {
        "heading": "Impairment of assets",
        "body": IMPAIRMENT_NOTE,
    },
    "Foreign currency translation (Section 30)": {
        "heading": "Foreign currency translation",
        "body": FOREIGN_CURRENCY_NOTE,
    },
    "Government grants (Section 24)": {
        "heading": "Government grants",
        "body": GOVERNMENT_GRANTS_NOTE,
    },
    "Borrowing costs (Section 25)": {
        "heading": "Borrowing costs",
        "body": BORROWING_COSTS_NOTE,
    },
    "Statement of cash flows (Section 7)": {
        "heading": "Statement of cash flows",
        "body": CASH_FLOW_NOTE,
    },
}
