# Changelog

<!--next-version-placeholder-->

## v0.4.3 (2024-06-05)

### Fix

* **RawImageDisplayArea:** Use proper array type for rgba ([`12857b8`](https://github.com/Kitware/trame-rca/commit/12857b81e8b8963b64f2717272efa7ccabc73541))
* **MediaSourceDisplayArea:** Adapt for wslink>=2 ([`de23267`](https://github.com/Kitware/trame-rca/commit/de232673ceff3f81d390012301c373c8425ce7d0))
* **VideoDecoder:** Flush before closing the decoder ([`4c484cf`](https://github.com/Kitware/trame-rca/commit/4c484cf1871d96d90ef3548b22d67c7d4a7a7343))
* **decoder:** Use .buffer when sending arrays ([`824c7a8`](https://github.com/Kitware/trame-rca/commit/824c7a89b2ee6898ae2050696388b33b63ca7fd2))
* **VideoDecoderDisplayArea:** Adapt for wslink>=2 ([`9c4a990`](https://github.com/Kitware/trame-rca/commit/9c4a990285f2b136cd0e78d4c8544dcdfcf86fa1))
* **vue:** Unmount components under both vue2 and vue3 ([`f779ee5`](https://github.com/Kitware/trame-rca/commit/f779ee5652495ad5b52421ba08c02912494e0d14))

## v0.4.2 (2024-05-13)

### Fix

* **wslink:** Add support for wslink>2 ([`813b6e2`](https://github.com/Kitware/trame-rca/commit/813b6e22be61c76070712ce76d72b7677f7b5021))

## v0.4.1 (2023-10-18)

### Fix

* **dependencies:** Update vtk-js ([`a694efe`](https://github.com/Kitware/trame-rca/commit/a694efe382e4eca6113be0095e44d4e9addb4818))

## v0.4.0 (2023-09-29)

### Feature

* **examples:** Add ViewAdapter example ([`80f6ba1`](https://github.com/Kitware/trame-rca/commit/80f6ba1b1b94fe506fc6f28c836c38d13ca9bfbf))
* **events:** Use mousebutton as eventType ([`b79052a`](https://github.com/Kitware/trame-rca/commit/b79052adac5a4e059e51f25ab8447b0680644b25))
* **events:** Forward start/end interaction events ([`6fd02a4`](https://github.com/Kitware/trame-rca/commit/6fd02a429ed2519c333b806381834dcfa4a5684d))
* **events:** Use vtk.js interactor ([`2819ab7`](https://github.com/Kitware/trame-rca/commit/2819ab72e0b7bd9fe8c12de2686bd179b5b52e36))
* **vue23:** Refactor code to be vue2/3 compatible ([`1d035a8`](https://github.com/Kitware/trame-rca/commit/1d035a8c16a6612632f3b41cd93346dba857f61f))

### Fix

* **pre-commit:** Handle black and flake8 conflict regarding W503 ([`23eb6b2`](https://github.com/Kitware/trame-rca/commit/23eb6b2c81416306a7509c3c2f42921276cc11b3))

## v0.3.1 (2023-04-25)
### Fix
* **api:** Expose only meaningful classes ([`3ccff7c`](https://github.com/Kitware/trame-rca/commit/3ccff7c53680a29f1249372d5b3d2f146e9e1af5))

## v0.3.0 (2022-10-27)
### Feature
* **RawImageDisplayArea:** Support rgb24 and rgba32 images ([`b77143a`](https://github.com/Kitware/trame-rca/commit/b77143a292e55148d060cae958053b1696fa1c08))

## v0.2.1 (2022-10-21)
### Fix
* **stats:** Allow stats to work on other pub/sub ([`b182e36`](https://github.com/Kitware/trame-rca/commit/b182e366cb5c2ffe718bced0d41e482f07c07b95))

## v0.2.0 (2022-10-16)
### Feature
* **VideoDisplayArea2:** Decode native vp9 bitstreams ([`43f4167`](https://github.com/Kitware/trame-rca/commit/43f41679c4c8ba6107ca4de6e568bd332cf5539d))

### Fix
* **VideoDecoder:** Code cleanup ([`32724b1`](https://github.com/Kitware/trame-rca/commit/32724b161262cbd6759c9293271afb7ef350bb07))
* **VideoDisplay:** Set source buffer in sequence mode ([`873ddc0`](https://github.com/Kitware/trame-rca/commit/873ddc0168a868f5a9f2c995c707f268df7a8f00))

## v0.1.3 (2022-10-14)
### Fix
* **stats:** Improve stats ([`396a74f`](https://github.com/Kitware/trame-rca/commit/396a74fe5dae764a4e1e3b8c8e9e0f90d3289122))

## v0.1.2 (2022-10-13)
### Fix
* **FpsDisplay:** Add fps feedback ([`2ddea8d`](https://github.com/Kitware/trame-rca/commit/2ddea8dbca6da7f531a795c0e77a8470d9be4cd4))

## v0.1.1 (2022-10-13)
### Fix
* **VideoDisplayArea:** Parse initialization segment ([`6dd4960`](https://github.com/Kitware/trame-rca/commit/6dd4960bbe75b59c763f597e4fab551bdcdc3661))

## v0.1.0 (2022-10-13)
### Feature
* **VideoDisplayArea:** Add video based DisplayArea ([`71d6e46`](https://github.com/Kitware/trame-rca/commit/71d6e46e2663d086e8ef2a011ac71a948144ee67))

### Fix
* **rca-widget:** Start handling mouse interaction ([`dd42f82`](https://github.com/Kitware/trame-rca/commit/dd42f82ebb3e796397b55246c8fed0f62fa366a7))
* **vue:** Size handling done at RCA rather than display ([`b47a944`](https://github.com/Kitware/trame-rca/commit/b47a94472d09a875f9e9c4d8b38f60c47138f538))
