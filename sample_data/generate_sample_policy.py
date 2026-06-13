"""
Generates a realistic mock commercial auto policy PDF for demo purposes.
Run once: python sample_data/generate_sample_policy.py
"""

from fpdf import FPDF

POLICY_SECTIONS = [
    ("DECLARATIONS PAGE", """
COMMERCIAL AUTO POLICY
Policy Number: CA-2024-BB-004521
Named Insured: Meridian Freight Solutions LLC
Address: 4821 Industrial Parkway, Dallas, TX 75201
Policy Period: 01/01/2025 to 01/01/2026 12:01 AM Standard Time
Business Description: Commercial Trucking and Freight Delivery

COVERAGES AND LIMITS
Liability Coverage: $1,000,000 Combined Single Limit
Personal Injury Protection: $10,000 per person
Uninsured Motorist: $100,000/$300,000
Comprehensive: Actual Cash Value, $1,000 deductible
Collision: Actual Cash Value, $2,500 deductible

SCHEDULED VEHICLES
Unit 01: 2021 Kenworth T680, VIN 1XKWDB9X0MJ123456, Garaging: Dallas TX 75201
Unit 02: 2020 Freightliner Cascadia, VIN 3AKJHHDR7LSLB2345, Garaging: Dallas TX 75201
Unit 03: 2022 Peterbilt 579, VIN 1XPBD49X1ND678901, Garaging: Fort Worth TX 76101

SCHEDULED DRIVERS
Driver 1: James Whitfield, DOB 03/14/1982, License TX-DL-4521987, CDL Class A
Driver 2: Maria Gonzalez, DOB 07/22/1990, License TX-DL-7834521, CDL Class A
Driver 3: Robert Chen, DOB 11/05/1978, License TX-DL-6123489, CDL Class B

STATED RADIUS OF OPERATIONS: 500 miles from garaging address
TERRITORY: Texas, Oklahoma, Louisiana, Arkansas, New Mexico
"""),

    ("SECTION I - COVERED AUTOS", """
INSURING AGREEMENT

We will pay all sums an insured legally must pay as damages because of bodily injury or
property damage to which this insurance applies, caused by an accident and resulting from
the ownership, maintenance or use of a covered auto.

We have the right and duty to defend any insured against a suit asking for such damages.
However, we have no duty to defend any insured against a suit seeking damages for bodily
injury or property damage or covered pollution cost or expense to which this insurance
does not apply.

COVERED AUTO SYMBOLS
Symbol 7 - Specifically described autos only. Only those autos described in Item Three
of the Declarations for which a premium charge is shown.

Symbol 8 - Hired autos only. Only those autos you lease, hire, rent or borrow.

Symbol 9 - Non-owned autos only. Only those autos you do not own, lease, hire, rent
or borrow that are used in connection with your business.
"""),

    ("SECTION II - LIABILITY COVERAGE", """
COVERAGE A - BODILY INJURY AND PROPERTY DAMAGE LIABILITY

We will pay those sums that the insured becomes legally obligated to pay as damages
because of bodily injury or property damage to which this insurance applies.

WHO IS AN INSURED
The following are insureds:
a. You for any covered auto.
b. Anyone else while using with your permission a covered auto you own, hire or borrow
   except a) The owner or anyone else from whom you hire or borrow a covered auto.
   b) Your employee if the covered auto is owned by that employee.
c. Anyone liable for the conduct of an insured described above but only to the extent
   of that liability.

PERMISSIVE USE
Coverage under this policy extends to any person using a covered auto with the Named
Insured's express or implied permission, provided such use is within the scope of the
permission granted and within the stated territory of operations.
"""),

    ("SECTION III - EXCLUSIONS", """
This insurance does not apply to any of the following:

EXCLUSION A - EXPECTED OR INTENDED INJURY
Bodily injury or property damage expected or intended from the standpoint of the insured.

EXCLUSION B - CONTRACTUAL LIABILITY
Liability assumed under any contract or agreement. However, this exclusion does not apply
to liability for damages that the insured would have in the absence of the contract.

EXCLUSION C - RADIUS RESTRICTION
This policy does not provide coverage for any loss arising out of the use of a covered
auto beyond the stated radius of operations shown in the Declarations (500 miles from the
garaging address). Coverage is suspended for any trip exceeding the stated radius unless
prior written endorsement CA 01 21 has been attached to this policy.

EXCLUSION D - POLLUTION
Bodily injury or property damage arising out of the actual, alleged or threatened
discharge, dispersal, seepage, migration, release or escape of pollutants. Pollutants
means any solid, liquid, gaseous or thermal irritant or contaminant, including smoke,
vapor, soot, fumes, acids, alkalis, chemicals and waste.

EXCLUSION E - RACING
Covered autos while used in any professional or organized racing or demolition contest
or stunting activity, or while practicing for such contest or activity.

EXCLUSION F - UNLISTED DRIVERS
This policy does not provide coverage for any loss arising out of the operation of a
covered auto by any person not listed on the Scheduled Drivers endorsement attached to
this policy. Coverage applies only to those drivers specifically named in the Declarations
or added by written endorsement. Casual or permissive use by unlisted drivers is
specifically excluded under this policy form.

EXCLUSION G - TERRITORY
This insurance applies only to accidents and losses which occur within the coverage
territory. The coverage territory is the United States of America, its territories and
possessions, Puerto Rico and Canada, but only within the states listed in the Declarations
as the Territory of Operations. Losses occurring in non-listed states are excluded.

EXCLUSION H - VEHICLE USE CLASSIFICATION
Coverage under this policy applies only to the use classification stated in the
Declarations. If a covered auto is used in a manner inconsistent with the stated
classification (e.g., a vehicle rated for local delivery used for long-haul interstate
freight), coverage may be voided for any loss arising during such non-classified use.
"""),

    ("SECTION IV - CONDITIONS", """
CONDITION A - DUTIES IN THE EVENT OF ACCIDENT, CLAIM, SUIT OR LOSS
In the event of accident, claim, suit or loss, you must:
a. Notify us promptly. Include how, when and where the accident or loss occurred.
b. Cooperate with us in the investigation, settlement or defense of the claim or suit.
c. Submit to examination under oath at our request.

CONDITION B - LEGAL ACTION AGAINST US
No one may bring a legal action against us under this Coverage Form until there has been
full compliance with all the terms of this Coverage Form.

CONDITION C - LOSS PAYMENT - PHYSICAL DAMAGE COVERAGES
At our option we may pay for, repair or replace damaged or stolen property.

CONDITION D - TRANSFER OF RIGHTS OF RECOVERY
If any person or organization to or for whom we make payment under this Coverage Form
has rights to recover damages from another, those rights are transferred to us.

CONDITION E - TERRITORY OF OPERATIONS
Coverage under this policy is restricted to the territory listed in the Declarations.
Operation of any covered auto outside the stated territory without prior written
authorization from the insurer will void coverage for any loss occurring outside
the approved territory.

CONDITION F - DRIVER QUALIFICATION
All drivers operating covered autos must maintain a valid commercial driver's license
appropriate for the vehicle class being operated. A Class B CDL holder may not operate
a vehicle requiring a Class A CDL. Any loss arising from operation by an unqualified
or improperly licensed driver is excluded from coverage.
"""),

    ("SECTION V - DEFINITIONS", """
DEFINITIONS

Accident means a sudden event, including continuous or repeated exposure to the same
conditions, resulting in bodily injury or property damage the insured did not expect
or intend.

Bodily injury means bodily harm, sickness or disease sustained by a person, including
death resulting from any of these.

Covered auto means any auto shown in the Declarations for which a premium is charged,
including any newly acquired auto.

Garaging address means the location where a covered auto is principally kept and stored
when not in use, as stated in the Declarations.

Pollutants means any solid, liquid, gaseous or thermal irritant or contaminant, including
smoke, vapor, soot, fumes, acids, alkalis, chemicals, waste and any material that is or
is claimed to be toxic or hazardous.

Radius of operations means the maximum distance from the garaging address within which
a covered auto is authorized to operate under this policy.

Territory of operations means those states specifically listed in the Declarations within
which coverage under this policy applies.

We, us, our means the Company providing this insurance.

You, your means the Named Insured shown in the Declarations.
"""),

    ("ENDORSEMENTS", """
ENDORSEMENT CA 04 44 - HIRED AUTO PHYSICAL DAMAGE
This endorsement modifies insurance provided under the Commercial Auto Coverage Form.
Physical damage coverage is extended to autos you hire, lease, rent or borrow, subject
to the same terms, conditions and deductibles as the owned auto physical damage coverage.

ENDORSEMENT CA 99 33 - POLICY CHANGES
Named Insured: Meridian Freight Solutions LLC
Policy Number: CA-2024-BB-004521

The following changes are made to the policy:
The scheduled drivers list is amended to include only those drivers listed in the
Declarations. Any driver not specifically listed is excluded from coverage under this
policy. This endorsement supersedes any permissive use language in the base policy form
with respect to unlisted drivers.

NOTE: Endorsement CA 01 21 (Radius Extension) has NOT been attached to this policy.
The standard 500-mile radius restriction in Exclusion C applies without modification.
""")
]


def generate_policy_pdf(output_path: str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for section_title, section_body in POLICY_SECTIONS:
        pdf.add_page()

        # Section header
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 10, section_title, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Section body
        pdf.set_font("Helvetica", size=10)
        effective_width = pdf.w - pdf.l_margin - pdf.r_margin
        for line in section_body.strip().split("\n"):
            if line.strip() == "":
                pdf.ln(3)
            else:
                pdf.multi_cell(effective_width, 5, line.strip())

    pdf.output(output_path)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    import os
    output = os.path.join(os.path.dirname(__file__), "sample_policy.pdf")
    generate_policy_pdf(output)
