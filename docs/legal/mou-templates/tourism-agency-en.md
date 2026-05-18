# Memorandum of Understanding — Tourism Agency White-Label Partnership

> **Status:** Template / starting point. Not legal advice. Counsel must review
> and adapt before any execution.

## 1. Parties

This Memorandum of Understanding ("MOU") is entered into between:

- **SilkLens** ("**Licensor**"), the operator of the SilkLens cultural-heritage
  platform; and
- **[Agency Legal Name]** ("**Partner**"), a tourism agency duly organised
  under the laws of **[Country]**, registered office at **[Address]**, tax ID
  **[Tax/VAT ID]**.

## 2. Scope of Licence

Subject to the terms below, Licensor grants Partner a non-exclusive,
non-transferable, revocable licence to operate a white-labelled tenant of
SilkLens under the brand **[Agency Brand]**. The licence covers:

- Web and mobile front-ends configured with Partner's logo, colour palette,
  and language pack;
- Access to Licensor's Heritage API, Search API, and AI inference for the
  registered users of Partner's tenant;
- Use of SilkLens trademarks solely in a "powered by SilkLens" attribution.

The licence does **not** include source-code access, the right to sub-licence,
or the right to operate a derivative platform.

## 3. Revenue Share / Royalty

Partner shall pay Licensor **[X]%** of net revenue arising from end-user
subscriptions, B2B listings, and AI credit purchases on the Partner tenant.
Net revenue means gross collected revenue minus payment-processor fees,
chargebacks, refunds, and applicable taxes. Settlement is monthly, due within
**[N]** days of the close of each calendar month, with a reconciliation report
attached. The revenue cut is recorded in `tenant_revenue_share`.

## 4. Data Residency

End-user PII originating in the European Union shall be stored in the EU
partition (`user_profiles_eu`); PII originating in Uzbekistan shall be stored
in the UZ partition (`user_profiles_uz`). Partner shall not export PII out of
its residency region without Licensor's prior written consent.

## 5. GDPR + UZ Compliance

Both parties are independent data controllers for the data each collects.
Partner shall implement the right-to-access, right-to-erasure, and
right-to-portability workflows surfaced via the Licensor compliance API.
Partner shall comply with the Uzbek Personal Data Law (No. ZRU-547) and
GDPR (EU 2016/679) as applicable.

## 6. Term and Termination

This MOU enters into force on the date of last signature and remains in
force for **one (1) year**, automatically renewing for successive one-year
terms unless either party gives **ninety (90)** days' written notice. Either
party may terminate immediately for material breach not cured within thirty
(30) days of written notice.

## 7. Signatures

| For Licensor | For Partner |
|--------------|-------------|
| Name: ________________ | Name: ________________ |
| Title: _______________ | Title: _______________ |
| Date: ________________ | Date: ________________ |
| Signature: ___________ | Signature: ___________ |
