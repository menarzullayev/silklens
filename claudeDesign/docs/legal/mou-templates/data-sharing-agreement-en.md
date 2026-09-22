# Data Sharing Agreement — Read-Only Heritage Data Exchange

> **Status:** Template / starting point. Not legal advice. Counsel must review
> and adapt before any execution.

## 1. Parties

This Data Sharing Agreement ("**Agreement**") is entered into between:

- **SilkLens** ("**Disclosing Party**" or "**Provider**"), the operator of
  the SilkLens cultural-heritage platform; and
- **[Organisation Name]** ("**Receiving Party**" or "**Consumer**"), a
  **[type: NGO / research institution / OTA / public body]** organised under
  the laws of **[Country]**.

## 2. Scope of Licence

Provider grants Receiving Party a non-exclusive, royalty-free, time-limited
licence to access read-only views of the SilkLens dataset for the purposes
listed in **Annex A** (research, public information, route planning, etc.).
Access is provided via the Enterprise API under a dedicated API key with
the `api_keys.scopes` array set to **[scope list]**.

The licence does **not** convey ownership, the right to sub-licence to third
parties, the right to redistribute raw datasets, or the right to use the
data for training machine-learning models without separate written consent.

## 3. Royalty / Cost Recovery

This Agreement is **non-commercial** unless otherwise specified. Where
Receiving Party uses the data in a commercial product, the parties shall
negotiate an attribution-plus-royalty addendum (default: **CC-BY 4.0** +
**[X]%** of attributable revenue, recorded against
`tenant_revenue_share.child_tenant_id` mapped to Receiving Party's tenant).

## 4. Data Residency

Provider shall serve the dataset from the residency region closest to
Receiving Party's lawful operating jurisdiction unless Receiving Party
explicitly opts into cross-region access in writing. Receiving Party shall
not duplicate the dataset outside that residency region beyond a working
copy needed for the agreed purpose, and shall delete derivatives on
termination.

## 5. GDPR + UZ + Local Compliance

Where any data shared under this Agreement is or becomes personal data,
Provider acts as data controller and Receiving Party acts as data processor
under EU GDPR Article 28; an addendum SCC (Standard Contractual Clauses)
shall be attached. Receiving Party shall comply with the Uzbek Personal
Data Law (No. ZRU-547) where applicable and shall surface a Data
Protection Officer contact in **Annex B**.

## 6. Term and Termination

This Agreement enters into force on the date of last signature and remains
in force for **two (2) years**, renewable in writing. Either party may
terminate on **sixty (60)** days' written notice. On termination the
Receiving Party shall delete or anonymise all data within thirty (30) days
and certify deletion in writing.

## 7. Signatures

| For Provider | For Receiving Party |
|--------------|---------------------|
| Name: ________________ | Name: ________________ |
| Title: _______________ | Title: _______________ |
| Date: ________________ | Date: ________________ |
| Signature: ___________ | Signature: ___________ |
